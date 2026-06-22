import type { Express } from "express";
import { type Server } from "http";
import http from "http";
import crypto from "crypto";
import { spawn, type ChildProcess } from "child_process";
import path from "path";
import fs from "fs";
import net from "net";
import { log } from "./index";

const FASTAPI_HOST = "127.0.0.1";
const FALLBACK_FASTAPI_PORT = 8002;
let fastapiProcess: ChildProcess | null = null;
let fastapiPort = parseFastAPIPort(process.env.FASTAPI_PORT) ?? FALLBACK_FASTAPI_PORT;

function parseFastAPIPort(value: string | undefined): number | null {
  if (!value) return null;
  const port = Number.parseInt(value, 10);
  return Number.isInteger(port) && port > 0 ? port : null;
}

function resolvePythonExecutable(projectRoot: string): string {
  const venvCandidates = [
    path.join(projectRoot, ".venv", "bin", "python"),
    path.join(projectRoot, ".venv", "Scripts", "python.exe"),
  ];

  for (const candidate of venvCandidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return process.platform === "win32" ? "python" : "python3";
}

function isPortAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const tester = net.createServer();

    tester.once("error", () => resolve(false));
    tester.once("listening", () => {
      tester.close(() => resolve(true));
    });

    tester.listen(port, FASTAPI_HOST);
  });
}

async function resolveFastAPIPort(): Promise<number> {
  const requestedPort = parseFastAPIPort(process.env.FASTAPI_PORT);
  const candidates = [
    requestedPort,
    FALLBACK_FASTAPI_PORT,
    8001,
    8003,
    8010,
  ].filter((value, index, arr): value is number => value !== null && arr.indexOf(value) === index);

  for (const candidate of candidates) {
    if (await isPortAvailable(candidate)) {
      return candidate;
    }
  }

  throw new Error(`Could not find an open FastAPI port among: ${candidates.join(", ")}`);
}

function startFastAPI(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (fastapiProcess) {
      resolve();
      return;
    }

    void (async () => {
      const projectRoot = path.resolve(process.cwd());
      const pythonExecutable = resolvePythonExecutable(projectRoot);
      fastapiPort = await resolveFastAPIPort();

      log(
        `Starting FastAPI server with ${pythonExecutable} on ${FASTAPI_HOST}:${fastapiPort}...`,
        "fastapi",
      );

      fastapiProcess = spawn(
        pythonExecutable,
        [
          "-m",
          "uvicorn",
          "api.main:app",
          "--host",
          FASTAPI_HOST,
          "--port",
          String(fastapiPort),
          "--log-level",
          "info",
          "--reload",
        ],
        {
          cwd: projectRoot,
          stdio: ["pipe", "pipe", "pipe"],
          env: { ...process.env },
        },
      );

      fastapiProcess.stdout?.on("data", (data: Buffer) => {
        const msg = data.toString().trim();
        if (msg) log(msg, "fastapi");
      });

      fastapiProcess.stderr?.on("data", (data: Buffer) => {
        const msg = data.toString().trim();
        if (msg) log(msg, "fastapi");
        if (msg.includes("Application startup complete") || msg.includes("Uvicorn running")) {
          resolve();
        }
      });

      fastapiProcess.on("error", (err) => {
        log(`FastAPI process error: ${err.message}`, "fastapi");
        reject(err);
      });

      fastapiProcess.on("exit", (code) => {
        log(`FastAPI process exited with code ${code}`, "fastapi");
      });

      setTimeout(() => resolve(), 5000);
    })().catch(reject);
  });
}

function proxyToFastAPI(
  req: any,
  res: any,
  targetPath: string
) {
  const originalHost = req.headers.host || "localhost:5000";
  const options: http.RequestOptions = {
    hostname: FASTAPI_HOST,
    port: fastapiPort,
    path: targetPath,
    method: req.method,
    headers: {
      ...req.headers,
      host: `${FASTAPI_HOST}:${fastapiPort}`,
      "x-forwarded-host": originalHost,
      "x-forwarded-proto": req.protocol || "http",
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on("error", (err) => {
    log(`Proxy error: ${err.message}`, "proxy");
    if (!res.headersSent) {
      res.status(502).json({ status: "error", message: "PDF API service unavailable" });
    }
  });

  if (req.rawBody) {
    proxyReq.write(req.rawBody);
    proxyReq.end();
  } else if (req.body && Object.keys(req.body).length > 0) {
    const bodyStr = JSON.stringify(req.body);
    proxyReq.setHeader("Content-Type", "application/json");
    proxyReq.setHeader("Content-Length", Buffer.byteLength(bodyStr));
    proxyReq.write(bodyStr);
    proxyReq.end();
  } else {
    proxyReq.end();
  }
}

function verifyApiKeyHeader(req: any): boolean {
  const apiKey = process.env.API_KEY || "";
  if (!apiKey) return false; // reject all requests when API_KEY is not configured
  const provided = String(req.headers["x-api-key"] || "");
  if (!provided) return false;
  try {
    const a = Buffer.from(provided.padEnd(apiKey.length));
    const b = Buffer.from(apiKey);
    if (a.length !== b.length) return false;
    return crypto.timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  await startFastAPI();

  app.get("/health", (req, res) => {
    proxyToFastAPI(req, res, "/health");
  });

  app.post("/generate-book-pdf", (req, res) => {
    proxyToFastAPI(req, res, "/generate-book-pdf");
  });

  app.post("/generate-cover", (req, res) => {
    proxyToFastAPI(req, res, "/generate-cover");
  });

  app.get(/^\/api\/download\/(.+)$/, (req, res) => {
    if (!verifyApiKeyHeader(req)) {
      return res.status(401).json({ status: "error", message: "Unauthorized: invalid or missing API key" });
    }
    const match = req.path.match(/^\/api\/download\/(.+)$/);
    if (!match) {
      return res.status(404).json({ status: "error", message: "File not found" });
    }
    const filePath = match[1];
    const storageBase = path.resolve(process.cwd(), "storage");
    const fullPath = path.resolve(storageBase, filePath);
    if (!fullPath.startsWith(storageBase + path.sep)) {
      return res.status(403).json({ status: "error", message: "Access denied" });
    }
    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ status: "error", message: "File not found" });
    }
    try {
      const stat = fs.statSync(fullPath);
      const fileName = path.basename(fullPath);
      log(`Serving download: ${fileName} (${(stat.size / 1024 / 1024).toFixed(2)} MB)`, "express");
      res.writeHead(200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${fileName}"`,
        "Content-Length": stat.size.toString(),
        "Cache-Control": "no-store",
      });
      const fileStream = fs.createReadStream(fullPath);
      fileStream.on("error", (streamErr) => {
        log(`Stream error for ${fileName}: ${streamErr.message}`, "express");
        if (!res.writableEnded) res.destroy();
      });
      req.on("close", () => {
        if (!fileStream.destroyed) fileStream.destroy();
      });
      fileStream.pipe(res);
    } catch (err: any) {
      log(`Download error: ${err.message}`, "express");
      if (!res.headersSent) {
        res.status(500).json({ status: "error", message: "Download failed" });
      }
    }
  });

  app.get("/api/example-payload", (_req, res) => {
    const examplePath = path.join(process.cwd(), "examples", "book_payload.json");
    try {
      const data = fs.readFileSync(examplePath, "utf-8");
      res.json(JSON.parse(data));
    } catch {
      res.status(404).json({ error: "Example payload not found" });
    }
  });

  process.on("exit", () => {
    if (fastapiProcess) {
      fastapiProcess.kill();
    }
  });

  return httpServer;
}
