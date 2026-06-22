import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  BookOpen,
  Send,
  Download,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  Copy,
  Zap,
  Code2,
  Server,
  KeyRound,
  ShieldCheck,
} from "lucide-react";

const EXAMPLE_CURL = `curl -X POST "https://your-app.replit.app/generate-book-pdf" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  --data @examples/book_payload.json`;

export default function Home() {
  const { toast } = useToast();
  const [jsonInput, setJsonInput] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [result, setResult] = useState<any>(null);

  const exampleQuery = useQuery({
    queryKey: ["/api/example-payload"],
  });

  const healthQuery = useQuery({
    queryKey: ["/health"],
    refetchInterval: 30000,
  });

  const generateMutation = useMutation({
    mutationFn: async (payload: string) => {
      const parsed = JSON.parse(payload);
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey.trim()) {
        headers["X-API-Key"] = apiKey.trim();
      }
      const response = await fetch("/generate-book-pdf", {
        method: "POST",
        headers,
        body: JSON.stringify(parsed),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || "Generation failed");
      }
      return data;
    },
    onSuccess: (data) => {
      setResult(data);
      toast({
        title: "PDF Generated",
        description: `${data.page_count} pages created with ${data.story_count} stories`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Generation Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const loadExample = () => {
    if (exampleQuery.data) {
      setJsonInput(JSON.stringify(exampleQuery.data, null, 2));
      toast({
        title: "Example Loaded",
        description: "Sample payload loaded into the editor",
      });
    }
  };

  const handleGenerate = () => {
    if (!jsonInput.trim()) {
      toast({
        title: "Empty Payload",
        description: "Please enter a JSON payload or load the example",
        variant: "destructive",
      });
      return;
    }
    try {
      JSON.parse(jsonInput);
    } catch {
      toast({
        title: "Invalid JSON",
        description: "Please fix the JSON syntax errors",
        variant: "destructive",
      });
      return;
    }
    generateMutation.mutate(jsonInput);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied", description: "Copied to clipboard" });
  };

  const handleDownload = async (downloadUrl: string, fileName: string) => {
    try {
      const isExternal = downloadUrl.includes("supabase.co/");
      if (isExternal) {
        // Supabase public URL — open directly (bypasses Replit proxy)
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = fileName;
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        // Local fallback — fetch through Express with API key
        const headers: Record<string, string> = {};
        if (apiKey.trim()) {
          headers["X-API-Key"] = apiKey.trim();
        }
        const response = await fetch(downloadUrl, { headers });
        if (!response.ok) {
          throw new Error(`Download failed with status ${response.status}`);
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
      toast({
        title: "Download Started",
        description: "Your PDF is downloading",
      });
    } catch (error) {
      toast({
        title: "Download Failed",
        description: error instanceof Error ? error.message : "Could not download file",
        variant: "destructive",
      });
    }
  };

  const isHealthy = healthQuery.data && (healthQuery.data as any).status === "ok";

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-md bg-primary flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight" data-testid="text-app-title">
                Memona Book PDF Generator
              </h1>
              <p className="text-xs text-muted-foreground">REST API for print-ready book interiors</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant={isHealthy ? "default" : "destructive"}
              data-testid="badge-health-status"
            >
              {isHealthy ? (
                <>
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Healthy
                </>
              ) : healthQuery.isLoading ? (
                <>
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Checking
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Offline
                </>
              )}
            </Badge>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        <section className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight" data-testid="text-hero-title">
            Generate Beautiful Print-Ready PDFs
          </h2>
          <p className="text-muted-foreground max-w-2xl">
            Send structured JSON with book metadata, stories, and styling to generate 
            professionally formatted 8x10" interior PDFs with QR codes, images, and 
            Azerbaijani locale formatting.
          </p>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card data-testid="card-feature-qr">
            <CardContent className="pt-6 flex gap-3">
              <div className="h-9 w-9 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                <Zap className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">QR Codes</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Auto-generated QR codes linking to audio recordings
                </p>
              </div>
            </CardContent>
          </Card>
          <Card data-testid="card-feature-layout">
            <CardContent className="pt-6 flex gap-3">
              <div className="h-9 w-9 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                <FileText className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Print Layout</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Mirrored margins, page numbers, and spread-aware images
                </p>
              </div>
            </CardContent>
          </Card>
          <Card data-testid="card-feature-api">
            <CardContent className="pt-6 flex gap-3">
              <div className="h-9 w-9 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
                <Server className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">REST API</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  JSON in, downloadable PDF links out. Simple integration.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="playground" className="space-y-4">
          <TabsList data-testid="tabs-main">
            <TabsTrigger value="playground" data-testid="tab-playground">
              <Code2 className="h-3.5 w-3.5 mr-1.5" />
              Playground
            </TabsTrigger>
            <TabsTrigger value="docs" data-testid="tab-docs">
              <FileText className="h-3.5 w-3.5 mr-1.5" />
              API Docs
            </TabsTrigger>
            <TabsTrigger value="curl" data-testid="tab-curl">
              <Server className="h-3.5 w-3.5 mr-1.5" />
              cURL
            </TabsTrigger>
          </TabsList>

          <TabsContent value="playground" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-base">Request Payload</CardTitle>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={loadExample}
                      disabled={exampleQuery.isLoading}
                      data-testid="button-load-example"
                    >
                      {exampleQuery.isLoading ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <FileText className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      Load Example
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="api-key" className="text-xs flex items-center gap-1.5">
                      <KeyRound className="h-3 w-3" />
                      API Key
                    </Label>
                    <Input
                      id="api-key"
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter your API key"
                      className="font-mono text-xs"
                      data-testid="input-api-key"
                    />
                  </div>
                  <Textarea
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    placeholder='{"book": {"title": "..."}, "stories": [...], ...}'
                    className="font-mono text-xs min-h-[350px] resize-none"
                    data-testid="input-json-payload"
                  />
                  <Button
                    onClick={handleGenerate}
                    disabled={generateMutation.isPending || !jsonInput.trim()}
                    className="w-full"
                    data-testid="button-generate"
                  >
                    {generateMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating PDF...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Generate PDF
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Response</CardTitle>
                </CardHeader>
                <CardContent>
                  {generateMutation.isPending ? (
                    <div className="flex flex-col items-center justify-center min-h-[400px] text-muted-foreground" data-testid="status-generating">
                      <Loader2 className="h-10 w-10 animate-spin mb-4 text-primary" />
                      <p className="font-medium">Generating your PDF...</p>
                      <p className="text-xs mt-1">This may take a few seconds for image-heavy books</p>
                    </div>
                  ) : result ? (
                    <div className="space-y-4" data-testid="container-result">
                      <div className="flex items-center gap-2 p-3 rounded-md bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900">
                        <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0" />
                        <div>
                          <p className="font-medium text-sm text-green-800 dark:text-green-300">PDF Generated Successfully</p>
                          <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                            {result.page_count} pages, {result.story_count} stories
                          </p>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 rounded-md bg-muted/50">
                          <span className="text-xs font-medium text-muted-foreground">File</span>
                          <span className="text-xs font-mono" data-testid="text-filename">{result.file_name}</span>
                        </div>
                        <div className="flex items-center justify-between p-2 rounded-md bg-muted/50">
                          <span className="text-xs font-medium text-muted-foreground">Storage Path</span>
                          <span className="text-xs font-mono truncate max-w-[200px]" data-testid="text-storage-path">{result.storage_path}</span>
                        </div>
                        <div className="flex items-center justify-between p-2 rounded-md bg-muted/50">
                          <span className="text-xs font-medium text-muted-foreground">Pages</span>
                          <span className="text-xs font-mono" data-testid="text-page-count">{result.page_count}</span>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="default"
                          size="sm"
                          className="flex-1"
                          onClick={() => handleDownload(result.download_url, result.file_name)}
                          data-testid="button-download"
                        >
                          <Download className="h-3.5 w-3.5 mr-1.5" />
                          Download PDF
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(result.download_url)}
                          data-testid="button-copy-url"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </Button>
                      </div>

                      <div className="mt-4">
                        <p className="text-xs font-medium text-muted-foreground mb-2">Raw Response</p>
                        <pre className="p-3 rounded-md bg-muted/50 text-xs font-mono overflow-auto max-h-[200px]" data-testid="text-raw-response">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : generateMutation.isError ? (
                    <div className="flex flex-col items-center justify-center min-h-[400px]" data-testid="status-error">
                      <AlertCircle className="h-10 w-10 text-destructive mb-4" />
                      <p className="font-medium text-destructive">Generation Failed</p>
                      <p className="text-xs text-muted-foreground mt-1 text-center max-w-xs">
                        {generateMutation.error?.message}
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center min-h-[400px] text-muted-foreground" data-testid="status-empty">
                      <BookOpen className="h-10 w-10 mb-4 opacity-30" />
                      <p className="font-medium">No response yet</p>
                      <p className="text-xs mt-1">Load the example payload and click Generate</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="docs" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">API Endpoints</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3" data-testid="docs-auth">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    <p className="font-medium text-sm">Authentication</p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    All endpoints except <code className="bg-muted px-1 rounded text-xs">/health</code> require
                    a valid API key sent via the <code className="bg-muted px-1 rounded text-xs">X-API-Key</code> header.
                    The server must have <code className="bg-muted px-1 rounded text-xs">API_KEY</code> configured in its environment —
                    requests are rejected with <code className="bg-muted px-1 rounded text-xs">401</code> if the env var is missing or the provided key does not match.
                  </p>
                  <pre className="p-3 rounded-md bg-muted/50 text-xs font-mono">
{`Header: X-API-Key: your-secret-key`}
                  </pre>
                  <p className="text-xs text-muted-foreground">
                    Returns <code className="bg-muted px-1 rounded">401 Unauthorized</code> if the key is missing, invalid, or not configured server-side.
                  </p>
                </div>

                <hr className="border-border" />

                <div className="space-y-3" data-testid="docs-health">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">GET</Badge>
                    <code className="text-sm font-mono">/health</code>
                    <Badge variant="outline" className="text-xs">Public</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">Check API health status (no auth required)</p>
                  <pre className="p-3 rounded-md bg-muted/50 text-xs font-mono">
{`Response: { "status": "ok" }`}
                  </pre>
                </div>

                <hr className="border-border" />

                <div className="space-y-3" data-testid="docs-generate">
                  <div className="flex items-center gap-2">
                    <Badge>POST</Badge>
                    <code className="text-sm font-mono">/generate-book-pdf</code>
                    <Badge variant="outline" className="text-xs">Auth Required</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Generate a print-ready interior PDF from structured JSON
                  </p>

                  <div className="space-y-2">
                    <p className="text-xs font-medium">Request Body</p>
                    <pre className="p-3 rounded-md bg-muted/50 text-xs font-mono overflow-auto max-h-[300px]">
{`{
  "book": {
    "title": "string (required, max 500 chars)",
    "subtitle": "string (optional)",
    "author": "string (optional)",
    "language": "string (default: 'az', max 10 chars)",
    "brand": "string (default: 'memona', max 50 chars)"
  },
  "style": {
    // Page size
    "page_size": "'8x10' | '6x9' | 'A4' | 'A5' | 'B5' | 'letter' | 'custom' (default: 'B5')",
    "custom_width_mm": "number 100–400 (required when page_size='custom')",
    "custom_height_mm": "number 100–500 (required when page_size='custom')",

    // Margins
    "margins_mm": {
      "inside": "number 5–50 (default: 24)",
      "outside": "number 5–50 (default: 20)",
      "top": "number 5–50 (default: 20)",
      "bottom": "number 5–50 (default: 22)"
    },

    // Typography
    "font_name": "'noto-serif' | 'libre-baskerville' | 'eb-garamond' | 'cormorant-garamond' | 'libertinus-serif' | 'taviraj' | 'crimson-pro' (default: 'libre-baskerville')",
    "body_font_size": "number 6–24 (default: 11)",
    "title_font_size": "number 12–48 (default: 21)",
    "date_font_size": "number 6–24 (default: 10)",
    "page_number_font_size": "number 6–24 (default: 9)",
    "contributor_font_size": "number 6–24 (default: 11)",
    "line_height": "number 1.0–3.0 (default: 1.55)",
    "paragraph_spacing": "number 0–2.0 (default: 0.4)",

    // Colors (6-digit hex)
    "body_text_color": "hex color (default: '#000000')",
    "date_color": "hex color (default: '#737373')",
    "divider_color": "hex color (default: '#B3B3B3')",
    "page_number_color": "hex color (default: '#666666')",
    "contributor_color": "hex color (default: '#8C8C8C')",
    "qr_color": "hex color (default: '#1A5C52')",
    "logo_color": "hex color (default: '#184b52')",

    // QR & logo
    "qr_code_size": "number 20–200 mm (default: 60)",
    "qr_logo_enabled": "boolean (default: true)",

    // Story opener spacing (mm)
    "qr_top_spacing": "number 0–100 (default: 10)",
    "title_spacing": "number 0–100 (default: 35)",
    "date_spacing": "number 0–100 (default: 10)",
    "divider_spacing": "number 0–100 (default: 14)",
    "story_top_spacing": "number 0–100 (default: 40)",
    "contributor_spacing": "number 0–100 (default: 8)",

    // Divider
    "divider_style": "'simple-line' | 'graduated-dots' | 'ornamental-floral' | 'line-with-heart' | 'line-with-diamond' | 'line-with-eyes' | 'line-with-circles' | 'ornamental-flat' (default: 'simple-line')",
    "divider_line_width": "number 0.1–5.0 (default: 0.5)",

    // Image styling
    "image_border_width": "number 0–5.0 (default: 0.5)",
    "image_border_color": "hex color (default: '#BFBFBF')",
    "image_border_padding": "number 0–20 mm (default: 4)",
    "full_page_image_margin": "number 0–50 mm (default: 0)",

    // Layout
    "show_page_numbers": "boolean (default: true)",
    "min_page_count": "integer 1–2000 (default: 200)",
    "print_cut_margin": "number 0–30 mm (default: 0)",
    "allow_reorder": "boolean — reorder stories to reduce filler pages (default: false)",
    "allow_reorder_count": "integer ≥0 — lookahead depth, 0 = unlimited (default: 0)"
  },
  "stories": [
    {
      "title": "string (required, max 1000 chars)",
      "body": "string (required)",
      "recorded_at": "ISO 8601 datetime (optional, e.g. '2024-06-15T14:30:00Z')",
      "qr_target_url": "URL string (required)",
      "image_urls": ["URL string", "URL string", "URL string"],
      "contributor": "string (optional) — name shown below story",
      "relation": "string (optional) — e.g. 'grandmother', shown with contributor"
    }
  ],
  "output": {
    "file_name": "string ending in .pdf (default: 'memona-book.pdf')"
  }
}`}
                    </pre>
                  </div>

                  <div className="space-y-2">
                    <p className="text-xs font-medium">Success Response (200)</p>
                    <pre className="p-3 rounded-md bg-muted/50 text-xs font-mono">
{`{
  "status": "ok",
  "file_name": "memona-book.pdf",
  "storage_path": "books/order-xxx/interior/memona-book.pdf",
  "download_url": "https://.../api/download/books/...",
  "page_count": 12,
  "story_count": 3
}`}
                    </pre>
                  </div>

                  <div className="space-y-2">
                    <p className="text-xs font-medium">Error Codes</p>
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                      <div className="p-2 rounded-md bg-muted/50">
                        <Badge variant="destructive" className="text-xs">401</Badge>
                        <p className="text-xs mt-1 text-muted-foreground">Missing or invalid API key</p>
                      </div>
                      <div className="p-2 rounded-md bg-muted/50">
                        <Badge variant="destructive" className="text-xs">400</Badge>
                        <p className="text-xs mt-1 text-muted-foreground">Validation/business error</p>
                      </div>
                      <div className="p-2 rounded-md bg-muted/50">
                        <Badge variant="destructive" className="text-xs">422</Badge>
                        <p className="text-xs mt-1 text-muted-foreground">Schema mismatch</p>
                      </div>
                      <div className="p-2 rounded-md bg-muted/50">
                        <Badge variant="destructive" className="text-xs">500</Badge>
                        <p className="text-xs mt-1 text-muted-foreground">Server error</p>
                      </div>
                    </div>
                  </div>
                </div>

                <hr className="border-border" />

                <div className="space-y-3" data-testid="docs-download">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">GET</Badge>
                    <code className="text-sm font-mono">/api/download/&#123;path&#125;</code>
                    <Badge variant="outline" className="text-xs">Auth Required</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">Download a generated PDF file</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Page Design Rules</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 rounded-md border">
                    <p className="font-medium text-sm">Stories without images</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      QR code → Title → Date → Divider → Body text flow
                    </p>
                  </div>
                  <div className="p-3 rounded-md border">
                    <p className="font-medium text-sm">Stories with images</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      New spread: Photo on left page, opener + text on right page
                    </p>
                  </div>
                  <div className="p-3 rounded-md border">
                    <p className="font-medium text-sm">Typography</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Noto Serif body (11pt), Bold titles (21pt), Sans dates (10pt)
                    </p>
                  </div>
                  <div className="p-3 rounded-md border">
                    <p className="font-medium text-sm">Page size</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      8×10" trim with mirrored inside/outside margins
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="curl" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-base">cURL Example</CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(EXAMPLE_CURL)}
                    data-testid="button-copy-curl"
                  >
                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                    Copy
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="p-4 rounded-md bg-muted/50 text-xs font-mono overflow-auto" data-testid="text-curl-example">
                  {EXAMPLE_CURL}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Start</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">1</div>
                    <div>
                      <p className="font-medium text-sm">Check health</p>
                      <pre className="mt-1 p-2 rounded-md bg-muted/50 text-xs font-mono">curl http://localhost:5000/health</pre>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">2</div>
                    <div>
                      <p className="font-medium text-sm">Prepare your JSON payload</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Use the example at <code className="bg-muted px-1 rounded">examples/book_payload.json</code> as a template
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">3</div>
                    <div>
                      <p className="font-medium text-sm">Send POST request</p>
                      <pre className="mt-1 p-2 rounded-md bg-muted/50 text-xs font-mono overflow-auto">
{`curl -X POST http://localhost:5000/generate-book-pdf \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  --data @examples/book_payload.json`}
                      </pre>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">4</div>
                    <div>
                      <p className="font-medium text-sm">Download the PDF</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Use the <code className="bg-muted px-1 rounded">download_url</code> from the response
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <footer className="pt-8 pb-4 border-t text-center">
          <p className="text-xs text-muted-foreground">
            Memona Book PDF Generator API v1.0.0
          </p>
        </footer>
      </main>
    </div>
  );
}
