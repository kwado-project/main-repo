"use client";
import { useRef, useState } from "react";
import useSWR from "swr";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Download, FileImage, FileText, Loader2, Lock, Sparkles, Trash2, UploadCloud, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, EmptyState, Input, Progress, Select, Skeleton } from "@/components/ui/primitives";
import { ConfirmDialog, Modal } from "@/components/ui/overlay";
import { Markdown } from "@/components/ui/markdown";
import { CreditCoin } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, getAccessToken, rawFetch, refreshSession } from "@/lib/api";
import { cn, fmtDate, uid } from "@/lib/utils";

const ACCEPT = ".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp";

export default function MaterialsPage() {
  const { data, mutate } = useSWR<any[]>("/materials", { refreshInterval: (d) => (d?.some((m: any) => m.status === "processing" || m.status === "uploaded" || (m.status === "ready" && !m.analysis && pendingAnalysis.has(m.id))) ? 3000 : 0) });
  const { data: progress } = useSWR<any[]>("/assessments/progress");
  const { data: pricing } = useSWR<any[]>("/wallet/pricing");
  const cost = pricing?.find((p) => p.key === "document_analysis")?.credits ?? 10;
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [pct, setPct] = useState<number | null>(null);
  const [confirm, setConfirm] = useState<any>(null);
  const [del, setDel] = useState<any>(null);
  const [view, setView] = useState<any>(null);
  const input = useRef<HTMLInputElement>(null);
  const toast = useToast();

  function pickFile(f?: File | null) {
    if (!f) return;
    if (f.size > 20 * 1024 * 1024) { toast({ tone: "error", title: "File too large", body: "Upload files under 20 MB." }); return; }
    setFile(f);
    setTitle(f.name.replace(/\.[^.]+$/, ""));
  }

  async function upload() {
    if (!file) return;
    await refreshSession();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title);
    if (subject) fd.append("subject", subject);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/materials");
    const t = getAccessToken();
    if (t) xhr.setRequestHeader("Authorization", `Bearer ${t}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && setPct((e.loaded / e.total) * 100);
    xhr.onload = () => {
      setPct(null);
      if (xhr.status === 201) { toast({ tone: "success", title: "Uploaded", body: "We're preparing your file." }); setFile(null); mutate(); }
      else { try { toast({ tone: "error", title: "Upload failed", body: JSON.parse(xhr.responseText).detail }); } catch { toast({ tone: "error", title: "Upload failed" }); } }
    };
    xhr.onerror = () => { setPct(null); toast({ tone: "error", title: "Upload failed", body: "Check your connection and try again." }); };
    setPct(0);
    xhr.send(fd);
  }

  async function analyse(m: any) {
    try {
      await api(`/materials/${m.id}/analyse`, { method: "POST", body: JSON.stringify({ idempotency_key: uid() }), headers: { "Content-Type": "application/json" } });
      pendingAnalysis.add(m.id);
      toast({ tone: "info", title: "Analysing…", body: "We'll notify you when it's ready." });
      mutate();
    } catch (e) {
      toast({ tone: "error", title: (e as ApiError).status === 402 ? "Not enough credits" : "Couldn't analyse", body: (e as ApiError).message });
    } finally { setConfirm(null); }
  }

  async function download(m: any) {
    const res = await rawFetch(`/materials/${m.id}/download`);
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) { const d = await res.json(); window.open(d.url, "_blank", "noopener"); return; }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = m.filename; a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold sm:text-3xl">Study materials</h1>
        <p className="mt-1 flex items-center gap-1.5 text-muted"><Lock className="h-4 w-4" /> Private to you. Upload notes and the AI tutor can use them when answering your questions.</p>
      </div>

      <section className="card p-5">
        <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pickFile(e.dataTransfer.files?.[0]); }}
          className={cn("flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition", drag ? "border-brand-500 bg-brand-50" : "border-line bg-canvas")}>
          <motion.span animate={drag ? { y: -6, scale: 1.1 } : { y: 0, scale: 1 }} className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-brand-600 shadow-card"><UploadCloud className="h-7 w-7" /></motion.span>
          <p className="mt-4 font-bold">Drag and drop a file here</p>
          <p className="text-sm text-muted">PDF, DOCX, TXT, PNG, JPG or WEBP · up to 20 MB</p>
          <Button variant="secondary" className="mt-4" onClick={() => input.current?.click()}>Choose file</Button>
          <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => pickFile(e.target.files?.[0])} />
        </div>
        <AnimatePresence>
          {file && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
              <div className="mt-4 grid gap-3 rounded-2xl border border-line p-4 sm:grid-cols-[auto_1fr_1fr_auto] sm:items-end">
                <div className="flex items-center gap-3"><FileIcon type={file.type} /><div className="min-w-0"><p className="max-w-[180px] truncate text-sm font-semibold">{file.name}</p><p className="text-xs text-muted">{(file.size / 1024 / 1024).toFixed(2)} MB</p></div></div>
                <div><label className="mb-1 block text-xs font-semibold">Title</label><Input value={title} onChange={(e) => setTitle(e.target.value)} className="h-10" /></div>
                <div><label className="mb-1 block text-xs font-semibold">Subject</label>
                  <Select value={subject} onChange={(e) => setSubject(e.target.value)} className="h-10"><option value="">General</option>{progress?.map((p) => <option key={p.subject.id} value={p.subject.id}>{p.subject.name}</option>)}</Select></div>
                <div className="flex gap-2"><Button variant="ghost" onClick={() => setFile(null)} disabled={pct !== null}>Cancel</Button><Button onClick={upload} loading={pct !== null}>Upload</Button></div>
              </div>
              {pct !== null && <Progress value={pct} className="mt-3" animateIn={false} />}
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <section>
        <h2 className="text-lg font-bold">Your files</h2>
        <div className="mt-3 grid gap-3">
          {!data && [0, 1].map((i) => <Skeleton key={i} className="h-20" />)}
          {data?.length === 0 && <div className="card"><EmptyState icon={FileText} title="No materials yet" body="Upload class notes, past handouts or textbook pages to study with AI." /></div>}
          {data?.map((m) => (
            <div key={m.id} className="card flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
              <FileIcon type={m.content_type} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{m.title}</p>
                <p className="text-xs text-muted">{[m.subject_name, `${(m.size_bytes / 1024 / 1024).toFixed(1)} MB`, fmtDate(m.created_at)].filter(Boolean).join(" · ")}</p>
                {m.error && <p className="mt-1 text-xs font-semibold text-red-600">{m.error}</p>}
              </div>
              <Status m={m} />
              <div className="flex gap-1.5">
                {m.analysis ? <Button size="sm" variant="soft" onClick={() => setView(m)}><Sparkles className="h-4 w-4" /> View analysis</Button>
                  : m.status === "ready" && <Button size="sm" onClick={() => setConfirm(m)} disabled={pendingAnalysis.has(m.id)}>{pendingAnalysis.has(m.id) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Analyse · {cost}</Button>}
                <Button size="icon" variant="ghost" onClick={() => download(m)} aria-label={`Download ${m.title}`}><Download className="h-4 w-4" /></Button>
                <Button size="icon" variant="ghost" onClick={() => setDel(m)} aria-label={`Delete ${m.title}`}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={() => analyse(confirm)} title="Analyse this document?" confirmLabel={`Use ${cost} credits`}
        body={<>The AI will summarise key concepts and write self-test questions. <span className="inline-flex items-center gap-1 font-semibold text-ink"><CreditCoin size={14} />{cost} credits</span> — refunded automatically if analysis fails.</>} />
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} danger confirmLabel="Delete" title="Delete this file?" body="It will be permanently removed from storage."
        onConfirm={async () => { await api(`/materials/${del.id}`, { method: "DELETE" }); setDel(null); mutate(); }} />
      <Modal open={!!view} onClose={() => setView(null)} title={view?.title} className="sm:max-w-2xl">{view && <Markdown>{view.analysis}</Markdown>}</Modal>
    </div>
  );
}

const pendingAnalysis = new Set<number>();

function FileIcon({ type }: { type: string }) {
  const img = type.startsWith("image/");
  return <span className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl", img ? "bg-sky-50 text-sky-600" : "bg-red-50 text-red-600")}>{img ? <FileImage className="h-5 w-5" /> : <FileText className="h-5 w-5" />}</span>;
}

function Status({ m }: { m: any }) {
  if (m.status === "ready") return <Badge><CheckCircle2 className="h-3 w-3" /> Ready</Badge>;
  if (m.status === "failed") return <Badge tone="red"><XCircle className="h-3 w-3" /> Failed</Badge>;
  return <Badge tone="amber"><Loader2 className="h-3 w-3 animate-spin" /> Processing</Badge>;
}
