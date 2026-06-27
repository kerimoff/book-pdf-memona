import { useState, useCallback, useRef } from "react";
import { PdfSpreadViewer } from "@/components/PdfSpreadViewer";
import { useMutation } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
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
import {
  BookOpen,
  Send,
  Download,
  Loader2,
  FileText,
  Plus,
  Trash2,
  Upload,
  FileDown,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

interface StoryState {
  title: string;
  body: string;
  recorded_at?: string;
  qr_target_url: string;
  image_urls?: string[];
}

interface LiveState {
  book: {
    title: string;
    subtitle: string;
    author: string;
    language: string;
    brand: string;
  };
  style: {
    page_size: string;
    custom_width_mm?: number;
    custom_height_mm?: number;
    font_name: string;
    body_font_size: number;
    title_font_size: number;
    line_height: number;
    paragraph_spacing: number;
    show_page_numbers: boolean;
    date_font_size: number;
    page_number_font_size: number;
    margins_mm: { inside: number; outside: number; top: number; bottom: number };
    qr_color: string;
    qr_logo_enabled: boolean;
    qr_code_size: number;
    qr_top_spacing: number;
    title_spacing: number;
    date_spacing: number;
    divider_spacing: number;
    story_top_spacing: number;
    divider_line_width: number;
    divider_style: string;
    image_border_width: number;
    image_border_color: string;
    image_border_padding: number;
    inline_photos_enabled: boolean;
    date_color: string;
    divider_color: string;
    page_number_color: string;
  };
  stories: StoryState[];
  output: { file_name: string };
}

// ── Default state (models.py defaults + small_example.json content) ──

const INITIAL_STATE: LiveState = {
  book: {
    title: "Xatirə Kitabı",
    subtitle: "Ailə hekayələri",
    author: "Memona",
    language: "az",
    brand: "memona",
  },
  style: {
    page_size: "B5",
    font_name: "libre-baskerville",
    body_font_size: 11,
    title_font_size: 21,
    line_height: 1.55,
    paragraph_spacing: 0.4,
    show_page_numbers: true,
    date_font_size: 10,
    page_number_font_size: 9,
    margins_mm: { inside: 24, outside: 20, top: 16, bottom: 18 },
    qr_color: "#1A5C52",
    qr_logo_enabled: true,
    qr_code_size: 60,
    qr_top_spacing: 10,
    title_spacing: 35,
    date_spacing: 10,
    divider_spacing: 14,
    story_top_spacing: 40,
    divider_line_width: 0.5,
    divider_style: "simple-line",
    image_border_width: 0.5,
    image_border_color: "#BFBFBF",
    image_border_padding: 4,
    inline_photos_enabled: true,
    date_color: "#737373",
    divider_color: "#B3B3B3",
    page_number_color: "#666666",
  },
  stories: [
    {
      title: "Nənəmin çörək təndiri",
      body: "Nənəmin həyətində bir təndir var idi — torpaqdan tikilmiş, böyürləri illərin istisindən qapqara olmuş. O təndir evin ürəyi idi. Çörək qoxusu küçəyə çıxanda qonşular bilirdi ki, cümə günüdür.\nHər cümə nənəm səhər tezdən qalxıb xəmiri yoğurardı. Böyük mis ləyəndə un, su, maya, bir çimdik duz. Əlləri qoca idi, barmaqları əyilmişdi, amma xəmiri elə yoğururdu ki, sanki rəqs edirdi. Mən kiçik idim, yanında oturub baxardım. Bəzən xəmir parçası qopardıb mənə verirdi: \"Al, sən də yoğur.\" Mənimki həmişə əlimə yapışardı. Nənəm gülürdü: \"Tələsmə, xəmir səni tanımalıdır.\"\nXəmir hazır olanda nənəm onu örtüb saxlayardı — deyirdi ki, xəmir yatmalıdır, nəfəs almalıdır. Sonra təndir zamanı gəlirdi. Od yandırırdı, alov divarları yalayırdı. Nənəm xəmiri nazik yayıb təndirin divarına yapışdırardı. O yapışma səsi — tap, tap, tap — indi də qulağımdadır.\nÇörəyin qızarma qoxusu bütün həyəti bürüyürdü. Qonşunun ağ pişiyi gəlib qapıda oturardı. Nənəm deyirdi: \"Bax, Ağbəniz də gəldi.\"\nTəndirdən çıxan ilk çörəyi həmişə qonşu Xədicə xalaya göndərirdi. \"Bərəkət paylaşmaqla gəlir\" — hər cümə eyni sözü deyirdi. Xədicə xala da cavab göndərirdi — bəzən pendir, bəzən üzüm.\nNənəm səksən yeddi yaşında vəfat etdi. Həyəti satdılar, təndir söküldü. Amma mən hər cümə, haradasa çörək qoxusu alanda nənəmin həyətinə qayıdıram. Əlləri unlu, üzündə sakit təbəssüm: \"Tələsmə, bala.\"",
      recorded_at: "2026-01-12T09:15:00.000Z",
      qr_target_url: "https://memona.app/blog",
    },
    {
      title: "Babamın dənizi ilk dəfə görməsi",
      body: "Babam Lənkəranda böyümüşdü — dağların ətəyində, çayların arasında, amma dənizdən uzaqda. Dənizi ilk dəfə on dörd yaşında görmüşdü. Bu hekayəni hər danışanda sanki yenidən yaşayırdı — gözləri böyüyürdü, səsi dəyişirdi, əlləri ilə dalğaları göstərirdi.\nDeyirdi ki, əmisi Rəhim onu Bakıya aparmışdı. Yük maşınının arxasında getmişdilər, brezent örtüyün altında, yanlarında alma yeşikləri. Yol çox uzun idi — indi maşınla dörd-beş saat deyirlər, amma o vaxt bütün gecə çəkmişdi. Yollar çuxur idi, maşın silkələnirdi, amma babam gözünü qırpmamışdı. Yatmaq ağlına belə gəlmirdi.\n\"Rəhim əmi, dəniz nə rəngdədir?\" — soruşmuşdu yolda. Əmisi gülmüşdü: \"Özün görərsən.\" Babam deyirdi ki, göy rəng təsəvvür edirdi, kitablardakı şəkillərdən. Amma gördüyü tamam başqa idi.\nSəhər tezdən Bakıya çatdılar. Əmisi onu birbaşa Bulvara apardı. Meydandan keçdilər, ağacların arasından çıxdılar, və birdən — dəniz.\nBabam həmişə bu cümləni eyni cür deyirdi: \"Mən bilmirdim ki, su bu qədər böyük ola bilər.\" Yerindəcə dayanmışdı, ağzı açıq. Əmisi arxadan gəlib çiyninə vurmuşdu: \"Nə oldu, qorxdun?\" Babam qorxmamışdı. Sözü gəlmirdi, vəssalam. Dil tutulmuşdu.\nDalğaların səsini eşidirdi — şırıltı, sonra geri çəkilmə, yenə şırıltı. Külək üzünə dəyirdi, dodaqlarında duz dadı hiss etdi. Quşlar havada fırlanırdı, ağ idi, qışqırırdılar. Hər şey yeni idi — səs, dad, qoxu, mənzərə. Beş duyğunun hamısı eyni anda partladı.\nSuya yaxınlaşdı, ayaqqabılarını çıxartdı. Ayağını saldı — soyuq idi, gözlədiyindən soyuq. Amma xoş idi. Dalğa gəldi, ayağını çəkib apardı, babam geri qaçdı. Sonra yenə irəli getdi. Dalğa yenə gəldi, yenə qaçdı. Bu oyunu saatlarla oynamışdı — dalğa ilə qaçış.\nƏmisi sahildə oturub papiros çəkirdi, baxıb gülürdü. \"Səni qoyub gedəcəm, sən çıxmayacaqsan suda\" — zarafat edirdi.\nAxşam əmisi ona dondurma aldı. Bulvarın girəcəyindəki arabadan — vanilli dondurma, vafli qıfda. Babam deyirdi ki, o günə qədər heç vaxt dondurma yeməmişdi. Birinci dişləmi heç vaxt unutmadı. \"Həyatımda yediyim ən dadlı şey\" — belə deyirdi. Biz gülürdük, çünki bilirdik ki, dondurmadan daha dadlı şeylər var. Amma o gün hər şeyin dadı fərqli idi, çünki hər şey ilk dəfə idi.\nBabam sonralar Bakıda yaşadı. Otuz il hər gün dənizi gördü, hər gün Bulvardan keçdi. Amma o ilk günün heyrəti heç vaxt getmədi. Deyirdi ki, insan bir şeyi ilk dəfə görəndə qəlbi başqa cür döyünür. Və o döyüntünü təkrarlamaq mümkün deyil — nə ikinci dəfə, nə üçüncü dəfə.\nBabam üç il əvvəl vəfat etdi. Ondan bir neçə həftə əvvəl birlikdə Bulvara getdik. Əlini tutub sahilə endirdim. O, əyilib əlini suya saldı — eynilə o on dörd yaşlı oğlan kimi. Barmaqlarını suda gəzdirdi, gözlərini yumdu.\n\"Hələ soyuqdur\" — dedi, sakit-sakit gülümsədi.\nBu, onun dənizlə son söhbəti idi.",
      recorded_at: "2026-02-20T14:00:00.000Z",
      qr_target_url: "https://memona.app/blog",
      image_urls: ["https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80"],
    },
    {
      title: "Atamın saatı",
      body: "Atamın bir cib saatı var idi. Gümüşü, köhnə, arxasında cızıqlar. Onu öz atasından almışdı, o da öz atasından. Üç nəslin saatı idi — üç kişinin cibindən keçmişdi, üç ömür görmüşdü.\nAtam hər səhər onu cibinə qoyurdu, hər axşam stolun üstünə. Saatın tıqqıltısı gecələr eşidilirdi — tıq-tıq-tıq — sanki evin ürəyi döyünürdü. Mən yatağımda o səslə yuxuya gedirdim. O səs yox olanda — atam səfərdə olanda — yata bilmirdim.\nBir dəfə soruşdum: \"Ata, bu saat düz gedir?\" Güldü: \"Beş dəqiqə geri qalır. Amma mən bunu bilirəm, ona görə əlli ildir heç vaxt gecikməmişəm. Əsas saat deyil, saatı tanımaqdır.\"\nSaatın şüşəsi bir dəfə çatlamışdı — atam düşürmüşdü. Bakıda bir usta tapdı, düzəltdirdi. Usta demişdi ki, saat qiymətlidir, çox köhnədir. Atam gülmüşdü: \"Qiymətini mən bilirəm, usta.\"\nAtam öləndə saatı mənə qaldı. Cibimə qoydum — isti idi hələ, sanki atamın istiliyi qalmışdı. İndi mənim cibimdir. Hələ beş dəqiqə geri qalır. Mən də əlli ildir heç vaxt gecikməmişəm.\nBir gün oğluma verəcəm. Dördüncü nəsil. Deyəcəm ki, beş dəqiqə geri qalır, amma saat yalan demir. Tanısan, kifayətdir.",
      recorded_at: "2025-07-18T11:00:00.000Z",
      qr_target_url: "https://memona.app/blog",
      image_urls: ["https://images.unsplash.com/photo-1509048191080-d2984bad6ae5?w=800&q=80"],
    },
    {
      title: "Toyumuzun gecəsi",
      body: "Toyumuz iyunun on yeddisi idi, min doqquz yüz səksən altı. Hava otuz beş dərəcə idi. Atam deyirdi ki, isti hava uğur gətirir. Anam deyirdi ki, atam hər şeydən uğur düzəltməyi bacarır.\nƏynimə yeni kostyum geymişdim — tünd göy, atam Bakıdan almışdı. Boyunbağımı düzəldə bilmirdim, əllərim titrəyirdi. Əmim gəlib düzəltdi: \"Qorxma, qaçmayacaq.\"\nHəyətdə süfrələr qurulmuşdu. Plov üç qazanda bişmişdi. Qonşu qadınlar kömək edirdi — dolma bükən, şəkərbura yoğuran, çay dəmləyən. Mətbəx xaos idi, amma gözəl xaos.\nUzaqdan zurna gəldi, baraban qoşuldu. Uşaqlar qaçdı: \"Gəlir!\" Fatimə maşından düşdü — ağ paltarda, ağ tülbənd. Gözləri tülbəndin altından parlayırdı. Əlləri titrəyirdi. Mənimkilər də.\nMərasim qısa oldu. Süfrə uzun. Gecə yarısı əmim lezginkanı elə oynayırdı ki, torpaq titrəyirdi. Kiçik bacım böyüklərin arasında fırlanırdı. Atam anamın əlindən tutub rəqs etdi — otuz il evli idilər, hələ utanırdılar.\nAmma ən yaxşı anı toyun sonunda idi. Qonaqlar dağıldı, musiqiçilər getdi. Biz ikimiz həyətdə tək qaldıq. Ulduzlar çox idi. Fatimə tülbəndini çıxartdı.\n\"Qorxdum ki, gəlməzsən\" — dedi.\n\"Hardaydım ki, gəlməyim? Bütün gün bu həyətdə oturmuşam.\"\nGüldü. Sakit, yorğun, xoşbəxt.\nQırx ildir Fatiməyləyik. Amma o gecəni — o sakit, ulduzlu gecəni — heç vaxt unutmadım.",
      recorded_at: "2026-03-01T11:45:00.000Z",
      qr_target_url: "https://memona.app/blog",
    },
  ],
  output: {
    file_name: "memona-book-update.pdf",
  },
};

// ── Page size, font & divider options ─────────────────────────────

const PAGE_SIZE_OPTIONS = [
  { value: "8x10", label: "8\u00d710 in (203\u00d7254 mm)" },
  { value: "6x9", label: "6\u00d79 in (152\u00d7229 mm)" },
  { value: "A4", label: "A4 (210\u00d7297 mm)" },
  { value: "A5", label: "A5 (148\u00d7210 mm)" },
  { value: "B5", label: "B5 (176\u00d7250 mm)" },
  { value: "letter", label: "Letter (216\u00d7279 mm)" },
  { value: "custom", label: "Custom..." },
];

const FONT_OPTIONS = [
  { value: "noto-serif", label: "Noto Serif" },
  { value: "libre-baskerville", label: "Libre Baskerville" },
  { value: "eb-garamond", label: "EB Garamond" },
  { value: "cormorant-garamond", label: "Cormorant Garamond" },
  { value: "libertinus-serif", label: "Libertinus Serif" },
  { value: "taviraj", label: "Taviraj" },
  { value: "crimson-pro", label: "Crimson Pro" },
];

const DIVIDER_OPTIONS = [
  { value: "simple-line", label: "Simple Line" },
  { value: "graduated-dots", label: "Graduated Dots" },
  { value: "ornamental-floral", label: "Ornamental Floral" },
  { value: "line-with-heart", label: "Line with Heart" },
  { value: "line-with-diamond", label: "Line with Diamond" },
  { value: "line-with-circles", label: "Line with Circles" },
  { value: "ornamental-flat", label: "Ornamental Flat" },
  { value: "line-with-eyes", label: "Line with Eyes" },
];

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

export default function Live() {
  const { toast } = useToast();
  const [state, setState] = useState<LiveState>(INITIAL_STATE);
  const [apiKey, setApiKey] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // State updaters
  const updateBook = useCallback(
    (key: string, value: string) =>
      setState((prev) => ({ ...prev, book: { ...prev.book, [key]: value } })),
    [],
  );

  const updateStyle = useCallback(
    (key: string, value: any) =>
      setState((prev) => ({
        ...prev,
        style: { ...prev.style, [key]: value },
      })),
    [],
  );

  const updateMargin = useCallback(
    (key: string, value: number) =>
      setState((prev) => ({
        ...prev,
        style: {
          ...prev.style,
          margins_mm: { ...prev.style.margins_mm, [key]: value },
        },
      })),
    [],
  );

  const updateStory = useCallback(
    (index: number, key: string, value: string) =>
      setState((prev) => ({
        ...prev,
        stories: prev.stories.map((s, i) =>
          i === index ? { ...s, [key]: value } : s,
        ),
      })),
    [],
  );

  const updateStoryPhoto = useCallback(
    (storyIdx: number, photoIdx: number, value: string) =>
      setState((prev) => ({
        ...prev,
        stories: prev.stories.map((s, i) => {
          if (i !== storyIdx) return s;
          const urls = [...(s.image_urls ?? [])];
          urls[photoIdx] = value;
          return { ...s, image_urls: urls };
        }),
      })),
    [],
  );

  const addStoryPhoto = useCallback(
    (storyIdx: number) =>
      setState((prev) => ({
        ...prev,
        stories: prev.stories.map((s, i) =>
          i === storyIdx
            ? { ...s, image_urls: [...(s.image_urls ?? []), ""] }
            : s,
        ),
      })),
    [],
  );

  const removeStoryPhoto = useCallback(
    (storyIdx: number, photoIdx: number) =>
      setState((prev) => ({
        ...prev,
        stories: prev.stories.map((s, i) =>
          i === storyIdx
            ? { ...s, image_urls: (s.image_urls ?? []).filter((_, j) => j !== photoIdx) }
            : s,
        ),
      })),
    [],
  );

  const addStory = useCallback(
    () =>
      setState((prev) => ({
        ...prev,
        stories: [
          ...prev.stories,
          {
            title: "New Story",
            body: "Story text here...",
            recorded_at: new Date().toISOString(),
            qr_target_url: "https://memona.app/blog",
          },
        ],
      })),
    [],
  );

  const removeStory = useCallback(
    (index: number) =>
      setState((prev) => ({
        ...prev,
        stories: prev.stories.filter((_, i) => i !== index),
      })),
    [],
  );

  // PDF generation
  const generateMutation = useMutation({
    mutationFn: async (payload: LiveState) => {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
      const response = await fetch("/generate-book-pdf", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Generation failed");
      return data;
    },
    onSuccess: async (data) => {
      // Fetch PDF as blob for iframe preview
      const downloadUrl: string = data.download_url;
      const isExternal = downloadUrl.includes("supabase.co/");
      const fetchUrl = isExternal ? downloadUrl : `/api/download/${data.storage_path}`;
      const headers: Record<string, string> = {};
      if (!isExternal && apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
      const res = await fetch(fetchUrl, { headers });
      const blob = await res.blob();
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
      toast({
        title: "PDF Generated",
        description: `${data.page_count} pages, ${data.story_count} stories`,
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

  const handleGenerate = () => generateMutation.mutate(state);

  const downloadMutation = useMutation({
    mutationFn: async (payload: LiveState) => {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
      const response = await fetch("/generate-book-pdf", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Generation failed");
      return data;
    },
    onSuccess: async (data) => {
      const downloadUrl: string = data.download_url;
      const isExternal = downloadUrl.includes("supabase.co/");
      if (isExternal) {
        // Supabase public URL — open directly
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = state.output.file_name || "output.pdf";
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        // Local fallback — fetch through Express with API key
        const headers: Record<string, string> = {};
        if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
        const res = await fetch(`/api/download/${data.storage_path}`, { headers });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = state.output.file_name || "output.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }
      toast({
        title: "PDF Downloaded",
        description: `${data.page_count} pages, ${data.story_count} stories`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Download Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleDownload = () => downloadMutation.mutate(state);

  const handleExport = () => {
    const json = JSON.stringify(state, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const name = state.book.title?.trim() || "live-params";
    a.download = `${name}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result as string) as LiveState;
        setState(parsed);
        toast({ title: "Parameters Imported", description: file.name });
      } catch {
        toast({
          title: "Import Failed",
          description: "Invalid JSON file",
          variant: "destructive",
        });
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm px-4 py-2.5 flex items-center gap-3 shrink-0">
        <a href="/" className="text-muted-foreground hover:text-foreground">
          <BookOpen className="h-5 w-5" />
        </a>
        <div className="flex-1">
          <h1 className="text-sm font-semibold">Live PDF Tuner</h1>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="API Key (optional)"
            className="w-40 h-8 text-xs"
          />
          <Button onClick={handleExport} size="sm" variant="outline">
            <FileDown className="h-4 w-4 mr-1" />
            Export
          </Button>
          <Button onClick={() => fileInputRef.current?.click()} size="sm" variant="outline">
            <Upload className="h-4 w-4 mr-1" />
            Import
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleImport}
            className="hidden"
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
            onClick={handleDownload}
            disabled={downloadMutation.isPending}
            size="sm"
            variant="outline"
          >
            {downloadMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Download className="h-4 w-4 mr-1" />
            )}
            Download
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
                defaultValue={["page-size", "typography", "margins", "book-info"]}
              >
                {/* ── Page Size ── */}
                <AccordionItem value="page-size">
                  <AccordionTrigger className="text-sm">
                    Page Size
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Size</Label>
                      <Select
                        value={state.style.page_size}
                        onValueChange={(v) => {
                          updateStyle("page_size", v);
                          if (v === "custom") {
                            updateStyle("custom_width_mm", 203.2);
                            updateStyle("custom_height_mm", 254);
                          } else {
                            updateStyle("custom_width_mm", undefined);
                            updateStyle("custom_height_mm", undefined);
                          }
                        }}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PAGE_SIZE_OPTIONS.map((s) => (
                            <SelectItem key={s.value} value={s.value}>
                              {s.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    {state.style.page_size === "custom" && (
                      <>
                        <SliderWithInput
                          label="Width (mm)"
                          value={state.style.custom_width_mm ?? 203.2}
                          onChange={(v) => updateStyle("custom_width_mm", v)}
                          min={100}
                          max={400}
                          step={0.1}
                        />
                        <SliderWithInput
                          label="Height (mm)"
                          value={state.style.custom_height_mm ?? 254}
                          onChange={(v) => updateStyle("custom_height_mm", v)}
                          min={100}
                          max={500}
                          step={0.1}
                        />
                      </>
                    )}
                  </AccordionContent>
                </AccordionItem>

                {/* ── Typography ── */}
                <AccordionItem value="typography">
                  <AccordionTrigger className="text-sm">
                    Typography
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Font</Label>
                      <Select
                        value={state.style.font_name}
                        onValueChange={(v) => updateStyle("font_name", v)}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {FONT_OPTIONS.map((f) => (
                            <SelectItem key={f.value} value={f.value}>
                              {f.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <SliderWithInput
                      label="Body Font Size (pt)"
                      value={state.style.body_font_size}
                      onChange={(v) => updateStyle("body_font_size", v)}
                      min={6}
                      max={24}
                      step={0.5}
                    />
                    <SliderWithInput
                      label="Title Font Size (pt)"
                      value={state.style.title_font_size}
                      onChange={(v) => updateStyle("title_font_size", v)}
                      min={12}
                      max={48}
                      step={1}
                    />
                    <SliderWithInput
                      label="Line Height"
                      value={state.style.line_height}
                      onChange={(v) => updateStyle("line_height", v)}
                      min={1.0}
                      max={3.0}
                      step={0.05}
                    />
                    <SliderWithInput
                      label="Paragraph Spacing"
                      value={state.style.paragraph_spacing}
                      onChange={(v) => updateStyle("paragraph_spacing", v)}
                      min={0}
                      max={2.0}
                      step={0.05}
                    />
                    <SliderWithInput
                      label="Date Font Size (pt)"
                      value={state.style.date_font_size}
                      onChange={(v) => updateStyle("date_font_size", v)}
                      min={6}
                      max={24}
                      step={0.5}
                    />
                    <SliderWithInput
                      label="Page Number Font Size (pt)"
                      value={state.style.page_number_font_size}
                      onChange={(v) => updateStyle("page_number_font_size", v)}
                      min={6}
                      max={24}
                      step={0.5}
                    />
                    <div className="flex items-center justify-between">
                      <Label className="text-xs">Show Page Numbers</Label>
                      <Switch
                        checked={state.style.show_page_numbers}
                        onCheckedChange={(v) =>
                          updateStyle("show_page_numbers", v)
                        }
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Margins ── */}
                <AccordionItem value="margins">
                  <AccordionTrigger className="text-sm">
                    Margins (mm)
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <SliderWithInput
                      label="Inside (spine)"
                      value={state.style.margins_mm.inside}
                      onChange={(v) => updateMargin("inside", v)}
                      min={5}
                      max={50}
                      step={1}
                    />
                    <SliderWithInput
                      label="Outside (trim)"
                      value={state.style.margins_mm.outside}
                      onChange={(v) => updateMargin("outside", v)}
                      min={5}
                      max={50}
                      step={1}
                    />
                    <SliderWithInput
                      label="Top"
                      value={state.style.margins_mm.top}
                      onChange={(v) => updateMargin("top", v)}
                      min={5}
                      max={50}
                      step={1}
                    />
                    <SliderWithInput
                      label="Bottom"
                      value={state.style.margins_mm.bottom}
                      onChange={(v) => updateMargin("bottom", v)}
                      min={5}
                      max={50}
                      step={1}
                    />
                  </AccordionContent>
                </AccordionItem>

                {/* ── QR Code ── */}
                <AccordionItem value="qr-code">
                  <AccordionTrigger className="text-sm">
                    QR Code
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <ColorInput
                      label="QR Color"
                      value={state.style.qr_color}
                      onChange={(v) => updateStyle("qr_color", v)}
                    />
                    <div className="flex items-center justify-between">
                      <Label className="text-xs">QR Logo Enabled</Label>
                      <Switch
                        checked={state.style.qr_logo_enabled}
                        onCheckedChange={(v) =>
                          updateStyle("qr_logo_enabled", v)
                        }
                      />
                    </div>
                    <SliderWithInput
                      label="QR Code Size (pt)"
                      value={state.style.qr_code_size}
                      onChange={(v) => updateStyle("qr_code_size", v)}
                      min={20}
                      max={200}
                      step={1}
                    />
                    <SliderWithInput
                      label="QR Top Spacing (pt)"
                      value={state.style.qr_top_spacing}
                      onChange={(v) => updateStyle("qr_top_spacing", v)}
                      min={0}
                      max={100}
                      step={1}
                    />
                  </AccordionContent>
                </AccordionItem>

                {/* ── Story Layout ── */}
                <AccordionItem value="story-layout">
                  <AccordionTrigger className="text-sm">
                    Story Opener Layout
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <SliderWithInput
                      label="Title Spacing (pt)"
                      value={state.style.title_spacing}
                      onChange={(v) => updateStyle("title_spacing", v)}
                      min={0}
                      max={100}
                      step={1}
                    />
                    <SliderWithInput
                      label="Date Spacing (pt)"
                      value={state.style.date_spacing}
                      onChange={(v) => updateStyle("date_spacing", v)}
                      min={0}
                      max={100}
                      step={1}
                    />
                    <SliderWithInput
                      label="Divider Spacing (pt)"
                      value={state.style.divider_spacing}
                      onChange={(v) => updateStyle("divider_spacing", v)}
                      min={0}
                      max={100}
                      step={1}
                    />
                    <SliderWithInput
                      label="Story Top Spacing (pt)"
                      value={state.style.story_top_spacing}
                      onChange={(v) => updateStyle("story_top_spacing", v)}
                      min={0}
                      max={100}
                      step={1}
                    />
                    <SliderWithInput
                      label="Divider Line Width (pt)"
                      value={state.style.divider_line_width}
                      onChange={(v) => updateStyle("divider_line_width", v)}
                      min={0.1}
                      max={5.0}
                      step={0.1}
                    />
                    <div className="space-y-1">
                      <Label className="text-xs">Divider Style</Label>
                      <Select
                        value={state.style.divider_style}
                        onValueChange={(v) => updateStyle("divider_style", v)}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {DIVIDER_OPTIONS.map((d) => (
                            <SelectItem key={d.value} value={d.value}>
                              {d.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Image Styling ── */}
                <AccordionItem value="image-styling">
                  <AccordionTrigger className="text-sm">
                    Image Styling
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <SliderWithInput
                      label="Border Width (pt)"
                      value={state.style.image_border_width}
                      onChange={(v) => updateStyle("image_border_width", v)}
                      min={0}
                      max={5.0}
                      step={0.1}
                    />
                    <ColorInput
                      label="Border Color"
                      value={state.style.image_border_color}
                      onChange={(v) => updateStyle("image_border_color", v)}
                    />
                    <SliderWithInput
                      label="Border Padding (pt)"
                      value={state.style.image_border_padding}
                      onChange={(v) => updateStyle("image_border_padding", v)}
                      min={0}
                      max={20}
                      step={1}
                    />
                    <div className="flex items-center justify-between">
                      <Label className="text-xs">Inline Photos Enabled</Label>
                      <Switch
                        checked={state.style.inline_photos_enabled}
                        onCheckedChange={(v) =>
                          updateStyle("inline_photos_enabled", v)
                        }
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Colors ── */}
                <AccordionItem value="colors">
                  <AccordionTrigger className="text-sm">
                    Colors
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4 px-1">
                    <ColorInput
                      label="Date Color"
                      value={state.style.date_color}
                      onChange={(v) => updateStyle("date_color", v)}
                    />
                    <ColorInput
                      label="Divider Color"
                      value={state.style.divider_color}
                      onChange={(v) => updateStyle("divider_color", v)}
                    />
                    <ColorInput
                      label="Page Number Color"
                      value={state.style.page_number_color}
                      onChange={(v) => updateStyle("page_number_color", v)}
                    />
                  </AccordionContent>
                </AccordionItem>

                <Separator className="my-2" />

                {/* ── Book Info ── */}
                <AccordionItem value="book-info">
                  <AccordionTrigger className="text-sm">
                    Book Info
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">Title</Label>
                      <Input
                        value={state.book.title}
                        onChange={(e) => updateBook("title", e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Subtitle</Label>
                      <Input
                        value={state.book.subtitle}
                        onChange={(e) => updateBook("subtitle", e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Author</Label>
                      <Input
                        value={state.book.author}
                        onChange={(e) => updateBook("author", e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1">
                        <Label className="text-xs">Language</Label>
                        <Input
                          value={state.book.language}
                          onChange={(e) =>
                            updateBook("language", e.target.value)
                          }
                          className="h-8 text-xs"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Brand</Label>
                        <Input
                          value={state.book.brand}
                          onChange={(e) => updateBook("brand", e.target.value)}
                          className="h-8 text-xs"
                        />
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Stories ── */}
                <AccordionItem value="stories">
                  <AccordionTrigger className="text-sm">
                    Stories ({state.stories.length})
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 px-1">
                    {state.stories.map((story, i) => (
                      <div
                        key={i}
                        className="border rounded-md p-3 space-y-2 bg-muted/30"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium truncate flex-1">
                            #{i + 1}: {story.title || "Untitled"}
                          </span>
                          {state.stories.length > 1 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-destructive"
                              onClick={() => removeStory(i)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Title</Label>
                          <Input
                            value={story.title}
                            onChange={(e) =>
                              updateStory(i, "title", e.target.value)
                            }
                            className="h-7 text-xs"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Body</Label>
                          <Textarea
                            value={story.body}
                            onChange={(e) =>
                              updateStory(i, "body", e.target.value)
                            }
                            className="text-xs min-h-[80px] max-h-[200px] resize-y"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="space-y-1">
                            <Label className="text-xs">Recorded At</Label>
                            <Input
                              value={story.recorded_at ?? ""}
                              onChange={(e) =>
                                updateStory(i, "recorded_at", e.target.value)
                              }
                              placeholder="Leave empty to hide date"
                              className="h-7 text-xs"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">QR Target URL</Label>
                            <Input
                              value={story.qr_target_url}
                              onChange={(e) =>
                                updateStory(i, "qr_target_url", e.target.value)
                              }
                              className="h-7 text-xs"
                            />
                          </div>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">
                            Photos (up to 3, optional)
                          </Label>
                          {(story.image_urls ?? []).map((url, photoIdx) => (
                            <div key={photoIdx} className="flex gap-1">
                              <Input
                                value={url}
                                onChange={(e) =>
                                  updateStoryPhoto(i, photoIdx, e.target.value)
                                }
                                className="h-7 text-xs"
                                placeholder="https://..."
                              />
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 shrink-0"
                                onClick={() => removeStoryPhoto(i, photoIdx)}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          ))}
                          {(story.image_urls ?? []).length < 3 && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full h-7 text-xs"
                              onClick={() => addStoryPhoto(i)}
                            >
                              <Plus className="h-3 w-3 mr-1" /> Add photo
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={addStory}
                    >
                      <Plus className="h-3 w-3 mr-1" /> Add Story
                    </Button>
                  </AccordionContent>
                </AccordionItem>

                {/* ── Output ── */}
                <AccordionItem value="output">
                  <AccordionTrigger className="text-sm">
                    Output
                  </AccordionTrigger>
                  <AccordionContent className="px-1">
                    <div className="space-y-1">
                      <Label className="text-xs">File Name</Label>
                      <Input
                        value={state.output.file_name}
                        onChange={(e) =>
                          setState((prev) => ({
                            ...prev,
                            output: { file_name: e.target.value },
                          }))
                        }
                        className="h-8 text-xs"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>
          </ScrollArea>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Right panel: PDF Preview */}
        <ResizablePanel defaultSize={60} minSize={30}>
          <div className="h-full flex flex-col bg-muted/30">
            {generateMutation.isPending ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <Loader2 className="h-10 w-10 animate-spin mb-4 text-primary" />
                <p className="font-medium text-sm">Generating PDF...</p>
              </div>
            ) : pdfUrl ? (
              <PdfSpreadViewer url={pdfUrl} />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <FileText className="h-10 w-10 mb-4 opacity-30" />
                <p className="font-medium text-sm">No PDF generated yet</p>
                <p className="text-xs mt-1">
                  Adjust parameters and click Generate
                </p>
              </div>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
