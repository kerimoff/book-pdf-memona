import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import type { PDFPageProxy, PDFDocumentLoadingTask } from "pdfjs-dist";

// Worker loaded from CDN – version matches the installed package at runtime
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

// ── Single spread row ────────────────────────────────────────────────────────

interface SpreadProps {
  /** 1-indexed page numbers in this spread (1 item = solo page, 2 = two-page spread) */
  pageNums: number[];
  allPages: PDFPageProxy[];
  /** Rendered pixel width of one page */
  pageWidth: number;
  /** When true, render a single page at full width without a blank left panel */
  fullWidth?: boolean;
}

function Spread({ pageNums, allPages, pageWidth, fullWidth }: SpreadProps) {
  const ref1 = useRef<HTMLCanvasElement>(null);
  const ref2 = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (pageWidth <= 0) return;
    const refs = [ref1, ref2];

    pageNums.forEach((num, idx) => {
      const page = allPages[num - 1];
      const canvas = refs[idx].current;
      if (!page || !canvas) return;

      const nativeVp = page.getViewport({ scale: 1 });
      const scale = pageWidth / nativeVp.width;
      const vp = page.getViewport({ scale });

      canvas.width = vp.width;
      canvas.height = vp.height;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      page.render({ canvasContext: ctx, viewport: vp });
    });
  }, [pageNums, allPages, pageWidth]);

  if (pageNums.length === 1) {
    if (fullWidth) {
      // Single page at full width (e.g. cover spread)
      return (
        <div className="flex shadow-md">
          <canvas ref={ref1} />
        </div>
      );
    }
    // Title page: blank left half + title on the right (recto position)
    return (
      <div className="flex shadow-md">
        <div
          className="bg-muted/60"
          style={{ width: pageWidth }}
          aria-hidden="true"
        />
        <canvas ref={ref1} />
      </div>
    );
  }

  return (
    <div className="flex shadow-md">
      <canvas ref={ref1} />
      <canvas ref={ref2} />
    </div>
  );
}

// ── Public component ─────────────────────────────────────────────────────────

interface Props {
  url: string;
  singlePageMode?: boolean;
}

export function PdfSpreadViewer({ url, singlePageMode }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pages, setPages] = useState<PDFPageProxy[]>([]);
  const [containerWidth, setContainerWidth] = useState(0);
  const [loading, setLoading] = useState(false);

  // Track container width with ResizeObserver
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setContainerWidth(entry.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Load PDF whenever the URL changes
  useEffect(() => {
    if (!url) return;

    let task: PDFDocumentLoadingTask | null = null;
    setLoading(true);
    setPages([]);

    task = pdfjs.getDocument(url);
    task.promise.then(async (doc) => {
      const loaded: PDFPageProxy[] = [];
      for (let i = 1; i <= doc.numPages; i++) {
        loaded.push(await doc.getPage(i));
      }
      setPages(loaded);
      setLoading(false);
    });

    return () => {
      task?.destroy();
    };
  }, [url]);

  // Build spread list: [[1], [2,3], [4,5], ...]
  const spreads: number[][] = [];
  if (pages.length > 0) {
    spreads.push([1]);
    for (let i = 2; i <= pages.length; i += 2) {
      spreads.push(
        i + 1 <= pages.length ? [i, i + 1] : [i],
      );
    }
  }

  // Each page occupies half the container width (minus a bit of outer padding)
  // In singlePageMode, pages use the full width
  const pageWidth = containerWidth > 0
    ? Math.floor((containerWidth - 32) / (singlePageMode ? 1 : 2))
    : 300;

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto bg-muted/40 flex flex-col items-center py-6 gap-8"
    >
      {loading && (
        <p className="text-sm text-muted-foreground mt-8">Rendering pages…</p>
      )}
      {spreads.map((spread, i) => (
        <Spread
          key={i}
          pageNums={spread}
          allPages={pages}
          pageWidth={pageWidth}
          fullWidth={singlePageMode}
        />
      ))}
    </div>
  );
}
