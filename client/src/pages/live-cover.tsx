import { useState, useCallback, useRef } from "react";
import { PdfSpreadViewer } from "@/components/PdfSpreadViewer";
import { useMutation } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { Separator } from "@/components/ui/separator";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  BookOpen,
  Send,
  Download,
  Loader2,
  FileText,
  Image as ImageIcon,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface CoverState {
  template: 1 | 2;
  title: string;
  subtitle: string;
  color: string;
  titleFont: string;
  titleFontSize: number;
  titleColor: string;
  subtitleFont: string;
  subtitleFontSize: number;
  subtitleColor: string;
  spineMode: "page_count" | "spine_width";
  pageCount: number;
  spineWidthMm: number;
  photoUrl: string;
}

const INITIAL_STATE: CoverState = {
  template: 1,
  title: "Xatirə Kitabı",
  subtitle: "Ailə hekayələri",
  color: "#2D6B5E",
  titleFont: "cormorant-garamond",
  titleFontSize: 30,
  titleColor: "#FFFFFF",
  subtitleFont: "noto-sans",
  subtitleFontSize: 15,
  subtitleColor: "#FFFFFF",
  spineMode: "page_count",
  pageCount: 200,
  spineWidthMm: 15,
  photoUrl: "",
};

// ── Options ────────────────────────────────────────────────────────

const COVER_FONT_OPTIONS = [
  { value: "cormorant-garamond", label: "Cormorant Garamond" },
  { value: "crimson-pro", label: "Crimson Pro" },
  { value: "eb-garamond", label: "EB Garamond" },
  { value: "libertinus-serif", label: "Libertinus Serif" },
  { value: "libre-baskerville", label: "Libre Baskerville" },
  { value: "noto-sans", label: "Noto Sans" },
  { value: "noto-serif", label: "Noto Serif" },
  { value: "taviraj", label: "Taviraj" },
];

function summarizeUnexpectedResponse(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "The server returned an empty response.";
  if (/<!DOCTYPE|<html/i.test(trimmed)) {
    return "The app returned HTML instead of JSON. This usually means the backend API failed to start correctly.";
  }

  return trimmed.replace(/\s+/g, " ").slice(0, 200);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(summarizeUnexpectedResponse(text));
  }
}

// ── Reusable sub-components ────────────────────────────────────────

function SliderWithInput({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <Input
          type="number"
          value={value}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v)) onChange(Math.min(max, Math.max(min, v)));
          }}
          min={min}
          max={max}
          step={step}
          className="w-20 h-7 text-xs text-right"
        />
      </div>
      <Slider
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={min}
        max={max}
        step={step}
      />
    </div>
  );
}

function ColorInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <Label className="text-xs flex-1">{label}</Label>
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        className="w-8 h-8 rounded border cursor-pointer p-0"
      />
      <Input
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          if (/^#[0-9A-Fa-f]{0,6}$/.test(v)) onChange(v.toUpperCase());
        }}
        className="w-24 h-7 text-xs font-mono"
        maxLength={7}
      />
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────

export default function LiveCover() {
  const { toast } = useToast();
  const [state, setState] = useState<CoverState>(INITIAL_STATE);
  const [apiKey, setApiKey] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [lastCoverPdfUrl, setLastCoverPdfUrl] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<"pdf" | "thumbnail">("pdf");

  const updateField = useCallback(
    <K extends keyof CoverState>(key: K, value: CoverState[K]) =>
      setState((prev) => ({ ...prev, [key]: value })),
    [],
  );

  // PDF generation
  const generateMutation = useMutation({
    mutationFn: async (coverState: CoverState) => {
      if (!coverState.photoUrl.trim()) throw new Error("Please provide a photo URL");

      const payload: Record<string, any> = {
        template: coverState.template,
        title: coverState.title,
        color: coverState.color,
        photo_url: coverState.photoUrl,
        title_font: coverState.titleFont,
        title_font_size: coverState.titleFontSize,
        title_color: coverState.titleColor,
        subtitle_font: coverState.subtitleFont,
        subtitle_font_size: coverState.subtitleFontSize,
        subtitle_color: coverState.subtitleColor,
      };
      if (coverState.subtitle.trim()) {
        payload.subtitle = coverState.subtitle;
      }
      if (coverState.spineMode === "page_count") {
        payload.page_count = coverState.pageCount;
      } else {
        payload.spine_width_mm = coverState.spineWidthMm;
      }

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();

      const response = await fetch("/generate-cover", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
      const data = await parseJsonResponse<{
        status: string;
        cover_pdf_url: string;
        thumbnail_url: string;
        message?: string;
      }>(response);
      if (!response.ok) throw new Error(data.message || "Cover generation failed");
      return data;
    },
    onSuccess: async (data) => {
      const coverPdfUrl = data.cover_pdf_url;
      const isExternal = coverPdfUrl.includes("supabase.co/");
      const fetchUrl = isExternal ? coverPdfUrl : coverPdfUrl;
      const headers: Record<string, string> = {};
      if (!isExternal && apiKey.trim()) headers["X-API-Key"] = apiKey.trim();

      const res = await fetch(fetchUrl, { headers });
      if (!res.ok) {
        throw new Error("Failed to download the generated cover PDF");
      }
      const blob = await res.blob();
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
      setLastCoverPdfUrl(coverPdfUrl);
      setThumbnailUrl(data.thumbnail_url);
      setPreviewMode("pdf");

      toast({
        title: "Cover Generated",
        description: "Cover PDF and thumbnail ready",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Cover Generation Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleGenerate = () => generateMutation.mutate(state);

  const downloadFile = useCallback(
    async (url: string, filename: string) => {
      try {
        const isExternal = url.includes("supabase.co/");
        if (isExternal) {
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          a.target = "_blank";
          document.body.appendChild(a);
          a.click();
          a.remove();
        } else {
          const headers: Record<string, string> = {};
          if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
          const res = await fetch(url, { headers });
          const blob = await res.blob();
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = blobUrl;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(blobUrl);
        }
      } catch {
        toast({
          title: "Download Failed",
          variant: "destructive",
        });
      }
    },
    [apiKey, toast],
  );

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm px-4 py-2.5 flex items-center gap-3 shrink-0">
        <a href="/" className="text-muted-foreground hover:text-foreground">
          <BookOpen className="h-5 w-5" />
        </a>
        <div className="flex-1">
          <h1 className="text-sm font-semibold">Live Cover Tuner</h1>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="API Key (optional)"
            className="w-40 h-8 text-xs"
          />
          <Button
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
            size="sm"
          >
            {generateMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Send className="h-4 w-4 mr-1" />
            )}
            Generate
          </Button>
          <Button
            onClick={() =>
              lastCoverPdfUrl && downloadFile(lastCoverPdfUrl, "cover_spread.pdf")
            }
            disabled={!lastCoverPdfUrl}
            size="sm"
            variant="outline"
          >
            <Download className="h-4 w-4 mr-1" />
            PDF
          </Button>
          <Button
            onClick={() =>
              thumbnailUrl && downloadFile(thumbnailUrl, "cover_thumb.png")
            }
            disabled={!thumbnailUrl}
            size="sm"
            variant="outline"
          >
            <ImageIcon className="h-4 w-4 mr-1" />
            Thumb
          </Button>
        </div>
      </header>

      {/* Main content */}
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left panel: Controls */}
        <ResizablePanel defaultSize={40} minSize={25}>
          <ScrollArea className="h-full">
            <div className="p-4 space-y-2">
              <Accordion
                type="multiple"
                defaultValue={[
                  "template",
                  "photo",
                  "cover-info",
                  "title-typo",
                  "subtitle-typo",
                  "color",
                  "spine",
                ]}
              >
                {/* ── Template ── */}
                <AccordionItem value="template">
                  <AccordionTrigger className="text-sm">
                    Template
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    <RadioGroup
                      value={String(state.template)}
                      onValueChange={(v) =>
                        updateField("template", Number(v) as 1 | 2)
                      }
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="1" id="t1" />
                        <Label htmlFor="t1" className="text-xs">
                          Classic — solid color, bordered photo, decorative lines
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="2" id="t2" />
                        <Label htmlFor="t2" className="text-xs">
                          Full Bleed — photo covers front+spine, solid back
                        </Label>
                      </div>
                    </RadioGroup>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Photo ── */}
                <AccordionItem value="photo">
                  <AccordionTrigger className="text-sm">
                    Photo
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Photo URL</Label>
                      <Input
                        value={state.photoUrl}
                        onChange={(e) =>
                          updateField("photoUrl", e.target.value)
                        }
                        placeholder="https://... (Supabase signed URL)"
                        className="h-8 text-xs"
                      />
                    </div>
                    {state.photoUrl.trim() && (
                      <img
                        src={state.photoUrl}
                        alt="Photo preview"
                        className="w-full rounded-md border max-h-40 object-contain bg-muted/30"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                        onLoad={(e) => {
                          (e.target as HTMLImageElement).style.display = "block";
                        }}
                      />
                    )}
                  </AccordionContent>
                </AccordionItem>

                {/* ── Cover Info ── */}
                <AccordionItem value="cover-info">
                  <AccordionTrigger className="text-sm">
                    Cover Info
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Title</Label>
                      <Input
                        value={state.title}
                        onChange={(e) =>
                          updateField("title", e.target.value)
                        }
                        className="h-8 text-xs"
                        maxLength={200}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Subtitle (optional)</Label>
                      <Input
                        value={state.subtitle}
                        onChange={(e) =>
                          updateField("subtitle", e.target.value)
                        }
                        className="h-8 text-xs"
                        maxLength={300}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                <Separator className="my-2" />

                {/* ── Title Typography ── */}
                <AccordionItem value="title-typo">
                  <AccordionTrigger className="text-sm">
                    Title Typography
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Font</Label>
                      <Select
                        value={state.titleFont}
                        onValueChange={(v) => updateField("titleFont", v)}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {COVER_FONT_OPTIONS.map((f) => (
                            <SelectItem key={f.value} value={f.value}>
                              {f.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <SliderWithInput
                      label="Font Size (pt)"
                      value={state.titleFontSize}
                      onChange={(v) => updateField("titleFontSize", v)}
                      min={12}
                      max={72}
                      step={1}
                    />
                    <ColorInput
                      label="Color"
                      value={state.titleColor}
                      onChange={(v) => updateField("titleColor", v)}
                    />
                  </AccordionContent>
                </AccordionItem>

                {/* ── Subtitle Typography ── */}
                <AccordionItem value="subtitle-typo">
                  <AccordionTrigger className="text-sm">
                    Subtitle Typography
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Font</Label>
                      <Select
                        value={state.subtitleFont}
                        onValueChange={(v) =>
                          updateField("subtitleFont", v)
                        }
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {COVER_FONT_OPTIONS.map((f) => (
                            <SelectItem key={f.value} value={f.value}>
                              {f.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <SliderWithInput
                      label="Font Size (pt)"
                      value={state.subtitleFontSize}
                      onChange={(v) => updateField("subtitleFontSize", v)}
                      min={8}
                      max={48}
                      step={1}
                    />
                    <ColorInput
                      label="Color"
                      value={state.subtitleColor}
                      onChange={(v) => updateField("subtitleColor", v)}
                    />
                  </AccordionContent>
                </AccordionItem>

                <Separator className="my-2" />

                {/* ── Color ── */}
                <AccordionItem value="color">
                  <AccordionTrigger className="text-sm">
                    Background Color
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    <ColorInput
                      label="Cover Color"
                      value={state.color}
                      onChange={(v) => updateField("color", v)}
                    />
                    <p className="text-xs text-muted-foreground">
                      {state.template === 1
                        ? "Used as the full background color"
                        : "Used for the back panel"}
                    </p>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Spine ── */}
                <AccordionItem value="spine">
                  <AccordionTrigger className="text-sm">
                    Spine
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    <RadioGroup
                      value={state.spineMode}
                      onValueChange={(v) =>
                        updateField(
                          "spineMode",
                          v as "page_count" | "spine_width",
                        )
                      }
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="page_count" id="sm-pc" />
                        <Label htmlFor="sm-pc" className="text-xs">
                          By Page Count
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="spine_width" id="sm-sw" />
                        <Label htmlFor="sm-sw" className="text-xs">
                          Direct Spine Width (mm)
                        </Label>
                      </div>
                    </RadioGroup>
                    {state.spineMode === "page_count" ? (
                      <SliderWithInput
                        label="Page Count"
                        value={state.pageCount}
                        onChange={(v) => updateField("pageCount", v)}
                        min={10}
                        max={1000}
                        step={1}
                      />
                    ) : (
                      <SliderWithInput
                        label="Spine Width (mm)"
                        value={state.spineWidthMm}
                        onChange={(v) => updateField("spineWidthMm", v)}
                        min={3}
                        max={80}
                        step={0.5}
                      />
                    )}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>
          </ScrollArea>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Right panel: Preview */}
        <ResizablePanel defaultSize={60} minSize={30}>
          <div className="h-full flex flex-col bg-muted/30">
            {/* Preview mode toggle */}
            {(pdfUrl || thumbnailUrl) && (
              <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
                <Button
                  variant={previewMode === "pdf" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPreviewMode("pdf")}
                >
                  PDF Spread
                </Button>
                <Button
                  variant={previewMode === "thumbnail" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPreviewMode("thumbnail")}
                >
                  Thumbnail
                </Button>
              </div>
            )}

            {generateMutation.isPending ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <Loader2 className="h-10 w-10 animate-spin mb-4 text-primary" />
                <p className="font-medium text-sm">Generating cover...</p>
              </div>
            ) : previewMode === "pdf" && pdfUrl ? (
              <PdfSpreadViewer url={pdfUrl} singlePageMode />
            ) : previewMode === "thumbnail" && thumbnailUrl ? (
              <div className="flex-1 flex items-center justify-center p-8">
                <img
                  src={thumbnailUrl}
                  alt="Cover thumbnail"
                  className="max-w-full max-h-full object-contain rounded-md shadow-lg"
                />
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <FileText className="h-10 w-10 mb-4 opacity-30" />
                <p className="font-medium text-sm">No cover generated yet</p>
                <p className="text-xs mt-1">
                  Set parameters and click Generate
                </p>
              </div>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
