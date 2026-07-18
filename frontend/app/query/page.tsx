"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence, useMotionValue, useSpring, useTransform } from "framer-motion";
import {
  Send, Loader2, RotateCcw, ChevronDown, ChevronUp,
  Upload, FileText, CheckCircle2, XCircle, X, MessageSquare,
  Hash, Mic, FileSpreadsheet, Image as ImageIcon, Sparkles, Brain,
} from "lucide-react";
import {
  queryKnowledge, ingestFile, ingestSlack, ingestAudio,
  ingestExcel, ingestImage, type QueryResponse,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import SourceCard from "@/components/SourceCard";
import AgentBadge from "@/components/AgentBadge";
import { validateFile, validateQuery, validateSlackChannel } from "@/lib/validation";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "Why did we migrate our database?",
  "Who decided to use LangGraph?",
  "What breaks if we remove Redis?",
  "What alternatives were considered for the auth system?",
];

type Tab = "query" | "upload" | "excel" | "audio" | "image" | "slack";
type IngestState = "idle" | "loading" | "success" | "error";

// ─────────────────────────────────────────────────────────────
// Mouse-tracking cursor glow hook
// ─────────────────────────────────────────────────────────────
function useMouseGlow(containerRef: React.RefObject<HTMLDivElement | null>) {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 120, damping: 22 });
  const springY = useSpring(mouseY, { stiffness: 120, damping: 22 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      mouseX.set(e.clientX - rect.left);
      mouseY.set(e.clientY - rect.top);
    };
    el.addEventListener("mousemove", handleMove);
    return () => el.removeEventListener("mousemove", handleMove);
  }, [containerRef, mouseX, mouseY]);

  return { springX, springY };
}

// ─────────────────────────────────────────────────────────────
// Scroll-reveal wrapper
// ─────────────────────────────────────────────────────────────
function FadeUp({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0.12 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 28 }}
      animate={visible ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────
// Progress bar for ingestion states
// ─────────────────────────────────────────────────────────────
function IngestProgressBar({ duration = 8 }: { duration?: number }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-center gap-3 py-3 px-5 glass rounded-xl border border-card-border text-foreground-muted text-sm font-medium">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
          <Loader2 size={16} className="text-accent" />
        </motion.div>
        Processing…
      </div>
      <div className="w-full h-0.5 rounded-full bg-card-border overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-accent via-accent-2 to-accent-3"
          initial={{ width: "0%" }}
          animate={{ width: "88%" }}
          transition={{ duration, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Drop zone component
// ─────────────────────────────────────────────────────────────
function DropZone({
  file, label, subLabel, accept, inputRef, onDrop, onSelect, onRemove,
  icon: Icon, state,
}: {
  file: File | null;
  label: string;
  subLabel: string;
  accept: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onDrop: (e: React.DragEvent) => void;
  onSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemove: () => void;
  icon: React.ElementType;
  state: IngestState;
}) {
  const [dragging, setDragging] = useState(false);

  return (
    <motion.div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { setDragging(false); onDrop(e); }}
      onClick={() => state !== "success" && inputRef.current?.click()}
      animate={{
        borderColor: dragging
          ? "var(--accent)"
          : file
          ? "var(--success)"
          : "var(--card-border)",
        backgroundColor: dragging
          ? "rgba(6,182,212,0.08)"
          : file
          ? "rgba(16,185,129,0.06)"
          : "transparent",
      }}
      whileHover={!file ? { borderColor: "var(--accent)", backgroundColor: "rgba(6,182,212,0.05)" } : {}}
      transition={{ duration: 0.25 }}
      className="rounded-2xl border-2 border-dashed cursor-pointer p-10 text-center"
      style={{ borderColor: "var(--card-border)" }}
    >
      <input ref={inputRef} type="file" accept={accept} onChange={onSelect} className="hidden" />
      {file ? (
        <div className="flex flex-col items-center gap-3">
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 280 }}
          >
            <Icon size={36} className="text-success" />
          </motion.div>
          <div>
            <p className="text-foreground font-medium text-sm">{file.name}</p>
            <p className="text-xs text-foreground-muted mt-0.5">
              {file.size < 1048576
                ? `${(file.size / 1024).toFixed(1)} KB`
                : `${(file.size / 1048576).toFixed(2)} MB`}
            </p>
          </div>
          {state !== "success" && (
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(); }}
              className="text-xs text-foreground-dim hover:text-danger transition-colors flex items-center gap-1"
            >
              <X size={12} /> Remove
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <motion.div animate={{ y: [0, -6, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}>
            <Icon size={36} className="text-foreground-dim" />
          </motion.div>
          <div>
            <p className="text-foreground text-sm font-medium">{label}</p>
            <p className="text-xs text-foreground-muted mt-1">{subLabel}</p>
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────
// Ingest success block
// ─────────────────────────────────────────────────────────────
function IngestSuccess({
  label, result: res, onQuery, onReset, resetLabel, inputRef,
}: {
  label: string;
  result: string | null;
  onQuery: () => void;
  onReset: () => void;
  resetLabel: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-4"
    >
      <div className="p-4 rounded-2xl border border-success/30 bg-success/10 flex items-start gap-3">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, delay: 0.2 }}
        >
          <CheckCircle2 size={18} className="text-success shrink-0 mt-0.5" />
        </motion.div>
        <div>
          <p className="text-sm text-success font-semibold">{label}</p>
          <p className="text-xs text-success/70 mt-0.5">
            Decisions extracted · stored in Neo4j + ChromaDB
          </p>
        </div>
      </div>

      {res && (
        <div className="glass rounded-2xl border border-card-border p-4">
          <p className="text-xs text-foreground-dim mb-2 font-semibold uppercase tracking-widest">
            Ingestion Result
          </p>
          <pre className="text-xs text-foreground-muted font-mono whitespace-pre-wrap leading-relaxed overflow-auto max-h-40">
            {res}
          </pre>
        </div>
      )}

      <div className="flex gap-3">
        <motion.button
          onClick={() => {
            onQuery();
            setTimeout(() => {
              inputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
              inputRef.current?.focus();
            }, 100);
          }}
          whileHover={{ scale: 1.03, y: -2 }}
          whileTap={{ scale: 0.97 }}
          className="flex-1 py-3 rounded-full text-white text-sm font-bold flex items-center justify-center gap-2 bg-gradient-to-r from-accent to-accent-2 shadow-lg shadow-accent/25"
        >
          <Send size={16} /> Query this now
        </motion.button>
        <motion.button
          onClick={onReset}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          className="px-4 py-2.5 rounded-xl border border-card-border text-foreground-muted hover:text-foreground text-sm transition-colors"
        >
          {resetLabel}
        </motion.button>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────
// Error block
// ─────────────────────────────────────────────────────────────
function IngestError({ error, onReset }: { error: string; onReset: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-2xl border border-danger/30 bg-danger/10 flex items-start gap-3"
    >
      <XCircle size={16} className="text-danger shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm text-danger font-semibold">Ingestion failed</p>
        <p className="text-xs text-danger/70 mt-1">{error}</p>
      </div>
      <button onClick={onReset} className="text-danger/50 hover:text-danger transition-colors">
        <RotateCcw size={14} />
      </button>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────
export default function QueryPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("query");
  const pageRef = useRef<HTMLDivElement>(null);

  // Mouse-parallax orbs
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const orbX = useSpring(rawX, { stiffness: 50, damping: 25 });
  const orbY = useSpring(rawY, { stiffness: 50, damping: 25 });
  const orbX2 = useTransform(orbX, v => -v * 0.6);
  const orbY2 = useTransform(orbY, v => -v * 0.6);

  useEffect(() => {
    const handle = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 60;
      const y = (e.clientY / window.innerHeight - 0.5) * 40;
      rawX.set(x);
      rawY.set(y);
    };
    window.addEventListener("mousemove", handle);
    return () => window.removeEventListener("mousemove", handle);
  }, [rawX, rawY]);

  // Search bar glow
  const glowX = useMotionValue(0);
  const glowY = useMotionValue(0);
  const transformGlowX = useTransform(glowX, v => v - 120);
  const transformGlowY = useTransform(glowY, v => v - 120);
  const [barFocus, setBarFocus] = useState(false);

  // ── Shared context ─────────────────────────────────────────
  const [contextLabel, setContextLabel] = useState<string | null>(null);
  const [sourceContext, setSourceContext] = useState<string | null>(null);

  useEffect(() => {
    const source = searchParams.get("source");
    const filename = searchParams.get("filename");
    if (source && filename) {
      setSourceContext(source);
      const icon = source.startsWith("document:") ? "📄" : source.startsWith("audio:") ? "🎵" : source.startsWith("image:") ? "🖼️" : "📁";
      setContextLabel(`${icon} ${filename}`);
    }
  }, [searchParams]);

  // ── Query state ────────────────────────────────────────────
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [showSources, setShowSources] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);

  // ── File states ────────────────────────────────────────────
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<IngestState>("idle");
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedExcel, setSelectedExcel] = useState<File | null>(null);
  const [excelState, setExcelState] = useState<IngestState>("idle");
  const [excelResult, setExcelResult] = useState<string | null>(null);
  const [excelError, setExcelError] = useState<string | null>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);

  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioState, setAudioState] = useState<IngestState>("idle");
  const [audioResult, setAudioResult] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageState, setImageState] = useState<IngestState>("idle");
  const [imageResult, setImageResult] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const [channelId, setChannelId] = useState("");
  const [msgLimit, setMsgLimit] = useState(100);
  const [slackState, setSlackState] = useState<IngestState>("idle");
  const [slackResult, setSlackResult] = useState<string | null>(null);
  const [slackError, setSlackError] = useState<string | null>(null);

  // ── Query ──────────────────────────────────────────────────
  async function handleSubmit(q?: string) {
    const query = q ?? question;
    const validationError = validateQuery(query);
    if (validationError) { setQueryError(validationError); return; }
    setQuestion("");
    setLoading(true);
    setQueryError(null);
    setResult(null);
    try {
      const data = await queryKnowledge(query, sourceContext || undefined);
      setResult(data);
    } catch (e) {
      setQueryError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  // ── PDF ────────────────────────────────────────────────────
  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file?.type === "application/pdf") setSelectedFile(file);
  }
  async function handleUpload() {
    if (!selectedFile) return;
    const validationError = validateFile(selectedFile, ["pdf"]);
    if (validationError) { setUploadState("error"); setUploadError(validationError); return; }
    setUploadState("loading"); setUploadError(null); setUploadResult(null);
    try {
      await ingestFile(selectedFile);
      window.dispatchEvent(new Event("recallai:files-changed"));
      setUploadState("success");
      setContextLabel(`📄 ${selectedFile.name}`);
      setSourceContext(`document:${selectedFile.name}`);
      setUploadResult("Ingestion completed successfully");
    } catch (e) {
      setUploadState("error");
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    }
  }
  function resetUpload() {
    setSelectedFile(null); setUploadState("idle"); setUploadResult(null);
    setUploadError(null); setSourceContext(null); setContextLabel(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // ── Excel ──────────────────────────────────────────────────
  function handleExcelDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    const ext = file?.name.toLowerCase().split(".").pop();
    if (ext === "xlsx" || ext === "xls") setSelectedExcel(file);
  }
  async function handleExcelUpload() {
    if (!selectedExcel) return;
    const validationError = validateFile(selectedExcel, ["xlsx", "xls"]);
    if (validationError) { setExcelState("error"); setExcelError(validationError); return; }
    setExcelState("loading"); setExcelError(null); setExcelResult(null);
    try {
      await ingestExcel(selectedExcel);
      window.dispatchEvent(new Event("recallai:files-changed"));
      setExcelState("success");
      setContextLabel(`📊 ${selectedExcel.name}`);
      setSourceContext(`document:${selectedExcel.name}`);
      setExcelResult("Ingestion completed successfully");
    } catch (e) {
      setExcelState("error");
      setExcelError(e instanceof Error ? e.message : "Excel upload failed");
    }
  }
  function resetExcel() {
    setSelectedExcel(null); setExcelState("idle"); setExcelResult(null);
    setExcelError(null); setSourceContext(null); setContextLabel(null);
    if (excelInputRef.current) excelInputRef.current.value = "";
  }

  // ── Slack ──────────────────────────────────────────────────
  async function handleSlackIngest() {
    const validationError = validateSlackChannel(channelId);
    if (validationError) { setSlackState("error"); setSlackError(validationError); return; }
    setSlackState("loading"); setSlackError(null); setSlackResult(null);
    try {
      await ingestSlack(channelId.trim(), msgLimit);
      window.dispatchEvent(new Event("recallai:files-changed"));
      setSlackState("success");
      setContextLabel(`💬 #${channelId.trim()}`);
      setSourceContext(`slack:${channelId.trim()}`);
      setSlackResult("Ingestion completed successfully");
    } catch (e) {
      setSlackState("error");
      setSlackError(e instanceof Error ? e.message : "Slack ingest failed");
    }
  }
  function resetSlack() {
    setChannelId(""); setMsgLimit(100); setSlackState("idle");
    setSlackResult(null); setSlackError(null); setSourceContext(null); setContextLabel(null);
  }

  // ── Audio ──────────────────────────────────────────────────
  async function handleAudioUpload() {
    if (!audioFile) return;
    const validationError = validateFile(audioFile, ["mp3", "wav", "m4a", "flac", "ogg", "mp4", "mov", "avi", "mkv", "webm"]);
    if (validationError) { setAudioState("error"); setAudioError(validationError); return; }
    setAudioState("loading"); setAudioError(null); setAudioResult(null);
    try {
      await ingestAudio(audioFile);
      window.dispatchEvent(new Event("recallai:files-changed"));
      setAudioState("success");
      setContextLabel(`🎵 ${audioFile.name}`);
      setSourceContext(`audio:${audioFile.name}`);
      setAudioResult("Ingestion completed successfully");
    } catch (e) {
      setAudioState("error");
      setAudioError(e instanceof Error ? e.message : "Audio ingest failed");
    }
  }
  function resetAudio() {
    setAudioFile(null); setAudioState("idle"); setAudioResult(null);
    setAudioError(null); setSourceContext(null); setContextLabel(null);
    if (audioInputRef.current) audioInputRef.current.value = "";
  }

  // ── Image ──────────────────────────────────────────────────
  function handleImageSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
      setImagePreviewUrl(URL.createObjectURL(file));
    }
  }
  async function handleImageUpload() {
    if (!imageFile) return;
    setImageState("loading"); setImageError(null); setImageResult(null);
    try {
      await ingestImage(imageFile);
      window.dispatchEvent(new Event("recallai:files-changed"));
      setImageState("success");
      setContextLabel(`🖼️ ${imageFile.name}`);
      setSourceContext(`image:${imageFile.name}`);
      setImageResult("Ingestion completed successfully");
    } catch (e) {
      setImageState("error");
      setImageError(e instanceof Error ? e.message : "Image ingest failed");
    }
  }
  function resetImage() {
    setImageFile(null); setImageState("idle"); setImageResult(null);
    setImageError(null); setSourceContext(null); setContextLabel(null);
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    setImagePreviewUrl(null);
    if (imageInputRef.current) imageInputRef.current.value = "";
  }

  // ── Tab switch ─────────────────────────────────────────────
  function switchTab(id: Tab) {
    if (id !== "query") {
      setSourceContext(null); setContextLabel(null);
      if (imagePreviewUrl) { URL.revokeObjectURL(imagePreviewUrl); setImagePreviewUrl(null); }
    }
    setTab(id);
  }

  const TABS: { id: Tab; label: string; icon: React.ElementType; color: string }[] = [
    { id: "query",  label: "Query",        icon: Brain,          color: "from-accent to-accent-2" },
    { id: "upload", label: "PDF",          icon: FileText,       color: "from-accent-2 to-accent-3" },
    { id: "excel",  label: "Excel",        icon: FileSpreadsheet, color: "from-accent-3 to-accent" },
    { id: "audio",  label: "Audio",        icon: Mic,            color: "from-warning to-accent-2" },
    { id: "image",  label: "Image OCR",   icon: ImageIcon,      color: "from-accent-3 to-warning" },
    { id: "slack",  label: "Slack",        icon: MessageSquare,  color: "from-accent to-accent-3" },
  ];

  const tabPanelVariants = {
    enter: { opacity: 0, y: 16, scale: 0.98 },
    center: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -10, scale: 0.98 },
  };

  return (
    <div ref={pageRef} className="relative min-h-screen overflow-hidden">
      {/* ── Parallax orbs ─────────────────────────────────────── */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <motion.div
          style={{ x: orbX, y: orbY }}
          className="orb orb-cyan absolute w-[600px] h-[600px] -top-48 -right-48 opacity-25"
        />
        <motion.div
          style={{ x: orbX2, y: orbY2 }}
          className="orb orb-violet absolute w-[500px] h-[500px] -bottom-32 -left-48 opacity-20"
        />
        <motion.div
          style={{ x: orbX, y: orbY2 }}
          className="orb orb-pink absolute w-[350px] h-[350px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-10"
        />
        {/* Grid lines */}
        <div className="absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage: "linear-gradient(var(--card-border) 1px, transparent 1px), linear-gradient(90deg, var(--card-border) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-6 py-24 md:py-32">

        {/* ── Header ──────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-14 text-center"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="inline-flex items-center gap-2 glass rounded-full px-5 py-2 text-xs font-bold text-foreground-muted border border-card-border mb-6 shadow-lg"
          >
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            >
              <Sparkles size={13} className="text-accent" />
            </motion.div>
            AI-Powered Knowledge Engine
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25 }}
            className="text-5xl md:text-7xl font-black font-display leading-none mb-5"
          >
            Knowledge{" "}
            <span className="text-gradient">Engine</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-lg text-foreground-muted max-w-2xl mx-auto leading-relaxed"
          >
            Ingest from Slack, PDF, Excel, Audio, or Images — then query across your entire organizational memory.
          </motion.p>
        </motion.div>

        {/* ── Tabs ────────────────────────────────────────────── */}
        <FadeUp delay={0.1} className="flex justify-center mb-10">
          <div className="inline-flex flex-wrap justify-center gap-2 p-2 rounded-3xl glass-strong border border-card-border shadow-2xl">
            {TABS.map(({ id, label, icon: Icon, color }, index) => (
              <motion.button
                key={id}
                onClick={() => switchTab(id)}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + index * 0.07 }}
                whileHover={{ scale: 1.07, y: -2 }}
                whileTap={{ scale: 0.95 }}
                className={`relative flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold transition-all duration-200 overflow-hidden ${
                  tab === id
                    ? "text-white shadow-lg"
                    : "text-foreground-muted hover:text-foreground"
                }`}
              >
                {tab === id && (
                  <motion.div
                    layoutId="activeTab"
                    className={`absolute inset-0 rounded-full bg-gradient-to-r ${color}`}
                    style={{ boxShadow: "0 0 20px rgba(6,182,212,0.35)" }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <motion.span
                  className="relative z-10"
                  animate={tab === id ? { rotate: [0, 10, -10, 0] } : {}}
                  transition={{ duration: 0.4 }}
                >
                  <Icon size={15} />
                </motion.span>
                <span className="relative z-10 whitespace-nowrap">{label}</span>
              </motion.button>
            ))}
          </div>
        </FadeUp>

        {/* ── Tab panels ──────────────────────────────────────── */}
        <AnimatePresence mode="wait">

          {/* ───── QUERY TAB ─────────────────────────────────── */}
          {tab === "query" && (
            <motion.div
              key="query"
              variants={tabPanelVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* Context banner */}
              <AnimatePresence>
                {contextLabel && (
                  <motion.div
                    initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                    animate={{ opacity: 1, height: "auto", marginBottom: 16 }}
                    exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                    className="flex items-center gap-3 px-4 py-3 rounded-2xl border border-success/30 bg-success/10 text-success text-xs overflow-hidden"
                  >
                    {imagePreviewUrl && sourceContext?.startsWith("image:") ? (
                      <img src={imagePreviewUrl} alt="" className="h-9 w-9 rounded-lg object-cover shrink-0 border border-success/30" />
                    ) : (
                      <CheckCircle2 size={14} />
                    )}
                    <span>
                      Querying only from{" "}
                      <span className="font-bold">{contextLabel}</span>
                    </span>
                    <button
                      onClick={() => { setContextLabel(null); setSourceContext(null); }}
                      className="ml-auto text-success/60 hover:text-success transition-colors"
                    >
                      <X size={13} />
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Search bar ── */}
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                whileHover={{ scale: 1.01 }}
                onMouseMove={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  glowX.set(e.clientX - rect.left);
                  glowY.set(e.clientY - rect.top);
                }}
                className="relative"
              >
                {/* Cursor-following inner glow */}
                <motion.div
                  className="absolute rounded-3xl pointer-events-none"
                  style={{
                    width: 240,
                    height: 240,
                    x: transformGlowX,
                    y: transformGlowY,
                    background: "radial-gradient(circle, rgba(6,182,212,0.3) 0%, rgba(139,92,246,0.1) 50%, transparent 85%)",
                    filter: "blur(20px)",
                    opacity: barFocus ? 1 : 0.5,
                  }}
                />

                {/* Outer glow ring when focused */}
                <AnimatePresence>
                  {barFocus && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="absolute -inset-px rounded-3xl pointer-events-none"
                      style={{
                        background: "linear-gradient(135deg, rgba(6,182,212,0.4), rgba(139,92,246,0.3))",
                        filter: "blur(8px)",
                        zIndex: -1,
                      }}
                    />
                  )}
                </AnimatePresence>

                <div
                  className={`relative flex items-center gap-3 glass-strong rounded-3xl border transition-colors duration-300 px-5 py-4 ${
                    barFocus ? "border-accent/60" : "border-card-border"
                  }`}
                >
                  <motion.div
                    animate={barFocus ? { scale: 1.15, color: "var(--accent)" } : { scale: 1 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Brain size={20} className="text-foreground-dim shrink-0" />
                  </motion.div>
                  <input
                    ref={inputRef}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    onFocus={() => setBarFocus(true)}
                    onBlur={() => setBarFocus(false)}
                    placeholder="Why did we choose React over Vue?"
                    className="flex-1 bg-transparent text-foreground placeholder:text-foreground-dim outline-none text-lg font-medium"
                  />
                  <motion.button
                    onClick={() => handleSubmit()}
                    disabled={loading || !question.trim()}
                    whileHover={{ scale: 1.12, rotate: 4 }}
                    whileTap={{ scale: 0.9, rotate: -4 }}
                    className="shrink-0 p-3.5 rounded-2xl text-white disabled:opacity-30 disabled:cursor-not-allowed bg-gradient-to-br from-accent to-accent-2 shadow-lg shadow-accent/30 transition-opacity"
                  >
                    {loading ? (
                      <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                        <Loader2 size={20} />
                      </motion.div>
                    ) : (
                      <Send size={20} />
                    )}
                  </motion.button>
                </div>
              </motion.div>

              {/* ── Loading ── */}
              <AnimatePresence>
                {loading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="mt-6 flex justify-start"
                  >
                    <motion.div
                      className="glass-strong px-6 py-4 rounded-2xl rounded-tl-sm border border-card-border flex items-center gap-3 text-sm font-semibold text-foreground-muted"
                      animate={{ boxShadow: ["0 0 0 0 rgba(6,182,212,0)", "0 0 30px 2px rgba(6,182,212,0.2)", "0 0 0 0 rgba(6,182,212,0)"] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                        <Loader2 size={16} className="text-accent" />
                      </motion.div>
                      <span>Thinking<motion.span animate={{ opacity: [1, 0, 1] }} transition={{ duration: 1.2, repeat: Infinity }}>…</motion.span></span>
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Result ── */}
              <AnimatePresence>
                {result && !loading && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                    className="mt-8 space-y-4"
                  >
                    <div className="flex items-center gap-2">
                      <AgentBadge agent={result.agent_used} />
                      <span className="text-xs text-foreground-dim">{result.reasoning}</span>
                    </div>
                    <motion.div
                      whileHover={{ scale: 1.005, y: -2 }}
                      transition={{ duration: 0.25 }}
                      className="glass-strong rounded-3xl p-6 border border-card-border text-foreground leading-relaxed whitespace-pre-wrap shadow-2xl"
                    >
                      {result.answer}
                    </motion.div>
                    {result.source_trace.length > 0 && (
                      <div>
                        <motion.button
                          onClick={() => setShowSources(v => !v)}
                          whileHover={{ x: 2 }}
                          className="flex items-center gap-1.5 text-xs text-foreground-dim hover:text-foreground transition-colors"
                        >
                          <motion.div animate={{ rotate: showSources ? 180 : 0 }} transition={{ duration: 0.3 }}>
                            <ChevronDown size={12} />
                          </motion.div>
                          {result.source_trace.length} source{result.source_trace.length > 1 ? "s" : ""}
                        </motion.button>
                        <AnimatePresence>
                          {showSources && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                              className="mt-3 space-y-2 overflow-hidden"
                            >
                              {result.source_trace.map((trace, j) => (
                                <motion.div
                                  key={j}
                                  initial={{ opacity: 0, x: -12 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: j * 0.07 }}
                                >
                                  <SourceCard trace={trace} />
                                </motion.div>
                              ))}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                    <div className="flex justify-center pt-2">
                      <motion.button
                        onClick={() => { setResult(null); setShowSources(false); inputRef.current?.focus(); }}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className="text-xs text-foreground-dim hover:text-foreground transition-colors flex items-center gap-1.5 glass px-4 py-2 rounded-full border border-card-border"
                      >
                        <RotateCcw size={12} /> New query
                      </motion.button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Error ── */}
              <AnimatePresence>
                {queryError && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="mt-6 p-4 rounded-2xl border border-danger/30 bg-danger/10 flex items-center gap-3"
                  >
                    <XCircle size={16} className="text-danger" />
                    <p className="text-sm text-danger">{queryError}</p>
                    <button onClick={() => setQueryError(null)} className="ml-auto text-danger/50 hover:text-danger">
                      <X size={14} />
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Suggestions ── */}
              {!result && !loading && !queryError && (
                <FadeUp delay={0.1} className="mt-8 space-y-4">
                  <p className="text-xs font-bold text-foreground-dim uppercase tracking-widest flex items-center gap-2">
                    <Sparkles size={11} className="text-accent" />
                    Try asking
                  </p>
                  <div className="flex flex-wrap gap-2.5">
                    {SUGGESTIONS.map((s, i) => (
                      <motion.button
                        key={s}
                        initial={{ opacity: 0, y: 14, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ delay: 0.15 + i * 0.08, type: "spring" }}
                        whileHover={{ scale: 1.06, y: -3, boxShadow: "0 8px 24px rgba(6,182,212,0.18)" }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => handleSubmit(s)}
                        className="text-sm px-5 py-2.5 rounded-full border border-card-border glass text-foreground-muted hover:text-foreground hover:border-accent/50 transition-all font-medium"
                      >
                        {s}
                      </motion.button>
                    ))}
                  </div>
                </FadeUp>
              )}
            </motion.div>
          )}

          {/* ───── UPLOAD PDF TAB ────────────────────────────── */}
          {tab === "upload" && (
            <motion.div key="upload" variants={tabPanelVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-5">
              <FadeUp>
                <p className="text-sm text-foreground-muted leading-relaxed">
                  Upload a PDF — the IngestionAgent extracts decisions, people, and context, then stores them in Neo4j + ChromaDB.
                </p>
              </FadeUp>
              <FadeUp delay={0.05}>
                <DropZone
                  file={selectedFile} label="Drop your PDF here" subLabel="or click to browse · PDF only"
                  accept="application/pdf" inputRef={fileInputRef}
                  onDrop={handleFileDrop} onSelect={(e) => { const f = e.target.files?.[0]; if (f) setSelectedFile(f); }}
                  onRemove={resetUpload} icon={FileText} state={uploadState}
                />
              </FadeUp>
              {selectedFile && uploadState === "idle" && (
                <FadeUp delay={0.1}>
                  <motion.button
                    onClick={handleUpload}
                    whileHover={{ scale: 1.03, y: -2 }}
                    whileTap={{ scale: 0.97 }}
                    className="w-full py-4 rounded-2xl text-white text-base font-bold flex items-center justify-center gap-3 bg-gradient-to-r from-accent to-accent-2 shadow-xl shadow-accent/20"
                  >
                    <Upload size={18} /> Ingest PDF
                  </motion.button>
                </FadeUp>
              )}
              {uploadState === "loading" && <IngestProgressBar duration={8} />}
              {uploadState === "error" && uploadError && <IngestError error={uploadError} onReset={resetUpload} />}
              {uploadState === "success" && (
                <IngestSuccess label="Document ingested successfully" result={uploadResult}
                  onQuery={() => { setContextLabel(`📄 ${selectedFile?.name}`); setSourceContext(`document:${selectedFile?.name}`); switchTab("query"); }}
                  onReset={resetUpload} resetLabel="Upload another" inputRef={inputRef}
                />
              )}
            </motion.div>
          )}

          {/* ───── EXCEL TAB ─────────────────────────────────── */}
          {tab === "excel" && (
            <motion.div key="excel" variants={tabPanelVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-5">
              <FadeUp>
                <p className="text-sm text-foreground-muted leading-relaxed">
                  Upload an Excel file — the IngestionAgent extracts decisions, people, and context, then stores them in Neo4j + ChromaDB.
                </p>
              </FadeUp>
              <FadeUp delay={0.05}>
                <DropZone
                  file={selectedExcel} label="Drop your Excel file here" subLabel="or click to browse · .xlsx or .xls"
                  accept=".xlsx,.xls" inputRef={excelInputRef}
                  onDrop={handleExcelDrop} onSelect={(e) => { const f = e.target.files?.[0]; if (f) setSelectedExcel(f); }}
                  onRemove={resetExcel} icon={FileSpreadsheet} state={excelState}
                />
              </FadeUp>
              {selectedExcel && excelState === "idle" && (
                <FadeUp delay={0.1}>
                  <motion.button
                    onClick={handleExcelUpload}
                    whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.97 }}
                    className="w-full py-4 rounded-2xl text-white text-base font-bold flex items-center justify-center gap-3 bg-gradient-to-r from-accent-3 to-accent shadow-xl shadow-accent/20"
                  >
                    <FileSpreadsheet size={18} /> Ingest Excel
                  </motion.button>
                </FadeUp>
              )}
              {excelState === "loading" && <IngestProgressBar duration={8} />}
              {excelState === "error" && excelError && <IngestError error={excelError} onReset={resetExcel} />}
              {excelState === "success" && (
                <IngestSuccess label="Excel ingested successfully" result={excelResult}
                  onQuery={() => { setContextLabel(`📊 ${selectedExcel?.name}`); setSourceContext(`document:${selectedExcel?.name}`); switchTab("query"); }}
                  onReset={resetExcel} resetLabel="Upload another" inputRef={inputRef}
                />
              )}
            </motion.div>
          )}

          {/* ───── AUDIO TAB ─────────────────────────────────── */}
          {tab === "audio" && (
            <motion.div key="audio" variants={tabPanelVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-5">
              <FadeUp>
                <p className="text-sm text-foreground-muted leading-relaxed">
                  Upload audio or video — we&apos;ll transcribe it using Whisper, then extract decisions and store them in Neo4j + ChromaDB.
                </p>
              </FadeUp>
              <FadeUp delay={0.05}>
                <DropZone
                  file={audioFile} label="Drop audio/video here" subLabel="or click to browse · MP3, WAV, MP4, MOV, etc."
                  accept="audio/*,video/*,.mp3,.wav,.m4a,.mp4,.mov,.avi,.mkv" inputRef={audioInputRef}
                  onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setAudioFile(f); }}
                  onSelect={(e) => { const f = e.target.files?.[0]; if (f) setAudioFile(f); }}
                  onRemove={resetAudio} icon={Mic} state={audioState}
                />
              </FadeUp>
              {audioFile && audioState === "idle" && (
                <FadeUp delay={0.1}>
                  <motion.button
                    onClick={handleAudioUpload}
                    whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.97 }}
                    className="w-full py-4 rounded-2xl text-white text-base font-bold flex items-center justify-center gap-3 bg-gradient-to-r from-warning to-accent-2 shadow-xl shadow-warning/20"
                  >
                    <Mic size={18} /> Transcribe &amp; Ingest
                  </motion.button>
                </FadeUp>
              )}
              {audioState === "loading" && <IngestProgressBar duration={15} />}
              {audioState === "error" && audioError && <IngestError error={audioError} onReset={resetAudio} />}
              {audioState === "success" && (
                <IngestSuccess label="Audio transcribed &amp; ingested" result={audioResult}
                  onQuery={() => { setContextLabel(`🎵 ${audioFile?.name}`); setSourceContext(`audio:${audioFile?.name}`); switchTab("query"); }}
                  onReset={resetAudio} resetLabel="Upload another" inputRef={inputRef}
                />
              )}
            </motion.div>
          )}

          {/* ───── IMAGE TAB ─────────────────────────────────── */}
          {tab === "image" && (
            <motion.div key="image" variants={tabPanelVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-5">
              <FadeUp>
                <p className="text-sm text-foreground-muted leading-relaxed">
                  Upload an image — we&apos;ll extract text using Groq Vision OCR, then extract decisions and store them in Neo4j + ChromaDB.
                </p>
              </FadeUp>
              <FadeUp delay={0.05}>
                <DropZone
                  file={imageFile} label="Drop image here" subLabel="or click to browse · PNG, JPG, GIF, WebP"
                  accept="image/*,.png,.jpg,.jpeg,.gif,.webp" inputRef={imageInputRef}
                  onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) { setImageFile(f); if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl); setImagePreviewUrl(URL.createObjectURL(f)); } }}
                  onSelect={handleImageSelect}
                  onRemove={resetImage} icon={ImageIcon} state={imageState}
                />
              </FadeUp>
              {imagePreviewUrl && (
                <FadeUp delay={0.08}>
                  <div className="glass rounded-2xl border border-card-border p-2 overflow-hidden">
                    <img src={imagePreviewUrl} alt="preview" className="w-full max-h-48 object-contain rounded-xl" />
                  </div>
                </FadeUp>
              )}
              {imageFile && imageState === "idle" && (
                <FadeUp delay={0.12}>
                  <motion.button
                    onClick={handleImageUpload}
                    whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.97 }}
                    className="w-full py-4 rounded-2xl text-white text-base font-bold flex items-center justify-center gap-3 bg-gradient-to-r from-accent-3 to-warning shadow-xl shadow-accent-3/20"
                  >
                    <ImageIcon size={18} /> Extract Text &amp; Ingest
                  </motion.button>
                </FadeUp>
              )}
              {imageState === "loading" && <IngestProgressBar duration={10} />}
              {imageState === "error" && imageError && <IngestError error={imageError} onReset={resetImage} />}
              {imageState === "success" && (
                <IngestSuccess label="Image OCR &amp; ingested" result={imageResult}
                  onQuery={() => { setContextLabel(`🖼️ ${imageFile?.name}`); setSourceContext(`image:${imageFile?.name}`); switchTab("query"); }}
                  onReset={resetImage} resetLabel="Upload another" inputRef={inputRef}
                />
              )}
            </motion.div>
          )}

          {/* ───── SLACK TAB ─────────────────────────────────── */}
          {tab === "slack" && (
            <motion.div key="slack" variants={tabPanelVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-5">
              <FadeUp>
                <p className="text-sm text-foreground-muted leading-relaxed">
                  Fetch messages from a Slack channel — the IngestionAgent extracts decisions and stores them in Neo4j + ChromaDB.
                </p>
              </FadeUp>

              <FadeUp delay={0.06}>
                <div className="glass-strong rounded-3xl border border-card-border p-6 space-y-6">
                  {/* Channel ID */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-foreground-dim uppercase tracking-widest flex items-center gap-1.5">
                      <Hash size={11} /> Channel ID
                    </label>
                    <div className="relative">
                      <Hash size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground-dim" />
                      <input
                        value={channelId}
                        onChange={(e) => setChannelId(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSlackIngest()}
                        placeholder="C0123456789"
                        disabled={slackState === "loading" || slackState === "success"}
                        className="glow-input w-full pl-10 pr-4 py-3 rounded-xl text-sm disabled:opacity-50"
                      />
                    </div>
                    <p className="text-xs text-foreground-dim">
                      Right-click channel → View channel details → Channel ID at the bottom.
                    </p>
                  </div>

                  {/* Message limit */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold text-foreground-dim uppercase tracking-widest">
                        Message Limit
                      </label>
                      <motion.span
                        key={msgLimit}
                        initial={{ scale: 1.3, color: "var(--accent)" }}
                        animate={{ scale: 1, color: "var(--foreground-muted)" }}
                        className="text-xs font-mono font-bold"
                      >
                        {msgLimit}
                      </motion.span>
                    </div>
                    <input
                      type="range" min={10} max={500} step={10} value={msgLimit}
                      onChange={(e) => setMsgLimit(Number(e.target.value))}
                      disabled={slackState === "loading" || slackState === "success"}
                      className="w-full accent-accent disabled:opacity-50 cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-foreground-dim">
                      <span>10</span><span>500</span>
                    </div>
                  </div>

                  {slackState !== "success" && (
                    <motion.button
                      onClick={handleSlackIngest}
                      disabled={!channelId.trim() || slackState === "loading"}
                      whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.97 }}
                      className="w-full py-4 rounded-2xl disabled:opacity-40 disabled:cursor-not-allowed text-white text-base font-bold flex items-center justify-center gap-3 bg-gradient-to-r from-accent to-accent-3 shadow-xl shadow-accent/20 transition-opacity"
                    >
                      {slackState === "loading" ? (
                        <>
                          <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                            <Loader2 size={18} />
                          </motion.div>
                          Fetching &amp; ingesting…
                        </>
                      ) : (
                        <><MessageSquare size={18} /> Ingest Channel</>
                      )}
                    </motion.button>
                  )}

                  {slackState === "loading" && (
                    <div className="w-full h-0.5 rounded-full bg-card-border overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-accent to-accent-3"
                        initial={{ width: "0%" }} animate={{ width: "85%" }}
                        transition={{ duration: 10, ease: "easeOut" }}
                      />
                    </div>
                  )}
                </div>
              </FadeUp>

              {slackState === "error" && slackError && <IngestError error={slackError} onReset={resetSlack} />}
              {slackState === "success" && (
                <IngestSuccess label={`#${channelId} ingested successfully`} result={slackResult}
                  onQuery={() => { setContextLabel(`💬 #${channelId}`); setSourceContext(`slack:${channelId}`); switchTab("query"); }}
                  onReset={resetSlack} resetLabel="Ingest another" inputRef={inputRef}
                />
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}
