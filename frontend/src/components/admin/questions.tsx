"use client";
import { useState } from "react";
import useSWR from "swr";
import { ArrowRight, Check, FileUp, Pencil, Plus, Search, ShieldCheck, Sparkles, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, EmptyState, Input, Label, Select, Skeleton, Textarea } from "@/components/ui/primitives";
import { Modal } from "@/components/ui/overlay";
import { Markdown } from "@/components/ui/markdown";
import { useToast } from "@/components/ui/toast";
import { StatusBadge, useDebounced } from "./resource";
import { api, ApiError, extractMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const FLOW = [
  { s: "draft", label: "Imported" }, { s: "validated", label: "Validated" }, { s: "answer_verified", label: "Answer verified" },
  { s: "in_review", label: "In review" }, { s: "published", label: "Published" },
];

export function QuestionBank() {
  const [status, setStatus] = useState("");
  const [subject, setSubject] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const params = new URLSearchParams({ page: String(page), ...(status && { status }), ...(subject && { subject }), ...(dq && { search: dq }) });
  const { data, mutate, isLoading } = useSWR<any>(`/admin-api/questions?${params}`);
  const { data: stats, mutate: mutateStats } = useSWR<Record<string, number>>("/admin-api/questions/stats");
  const { data: subjects } = useSWR<any>("/admin-api/subjects?page_size=100");
  const [open, setOpen] = useState<any>(null);
  const [editing, setEditing] = useState<any>(null);
  const [importing, setImporting] = useState(false);
  const reload = () => { mutate(); mutateStats(); };

  return (
    <div>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div><h1 className="text-2xl font-extrabold">Question bank</h1><p className="mt-1 text-sm text-muted">Import → Validate → Verify answer → Review → Publish. Only published questions with a human-verified answer key reach students.</p></div>
        <div className="flex gap-2"><Button variant="secondary" onClick={() => setImporting(true)}><FileUp className="h-4 w-4" /> Import</Button><Button onClick={() => setEditing({ options: [{ label: "A", text: "" }, { label: "B", text: "" }, { label: "C", text: "" }, { label: "D", text: "" }], difficulty: 2 })}><Plus className="h-4 w-4" /> New question</Button></div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-6">
        {[...FLOW, { s: "rejected", label: "Rejected" }].map((f) => (
          <button key={f.s} onClick={() => { setStatus(status === f.s ? "" : f.s); setPage(1); }} className={cn("rounded-xl border p-3 text-left transition", status === f.s ? "border-brand-600 bg-brand-50" : "border-line bg-white hover:border-brand-300")}>
            <p className="text-xl font-extrabold">{stats?.[f.s] ?? 0}</p><p className="text-xs font-semibold text-muted">{f.label}</p>
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1"><Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><Input className="h-11 pl-10" placeholder="Search question text…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} /></div>
        <Select className="sm:w-56" value={subject} onChange={(e) => { setSubject(e.target.value); setPage(1); }} aria-label="Subject"><option value="">All subjects</option>{subjects?.results?.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select>
      </div>

      <div className="card mt-4 divide-y divide-line">
        {isLoading && [0, 1, 2].map((i) => <div key={i} className="p-4"><Skeleton className="h-10" /></div>)}
        {data?.results?.length === 0 && <EmptyState icon={Search} title="No questions match" />}
        {data?.results?.map((r: any) => (
          <button key={r.id} onClick={() => setOpen(r)} className="flex w-full items-start gap-3 p-4 text-left hover:bg-slate-50">
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-sm font-semibold">{r.text}</p>
              <p className="mt-1 text-xs text-muted">{r.subject_name}{r.topic_name ? ` · ${r.topic_name}` : ""} · {["", "Easy", "Medium", "Hard"][r.difficulty]}{r.exam_year ? ` · ${r.exam_year}` : ""}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <StatusBadge value={r.status} />
              {r.is_ai_generated && <Badge tone="amber"><Sparkles className="h-3 w-3" /> AI</Badge>}
            </div>
          </button>
        ))}
        {data && (
          <div className="flex items-center justify-between px-4 py-3 text-sm">
            <span className="text-muted">{data.count} questions</span>
            <div className="flex gap-2"><Button size="sm" variant="ghost" disabled={!data.previous} onClick={() => setPage(page - 1)}>Previous</Button><Button size="sm" variant="ghost" disabled={!data.next} onClick={() => setPage(page + 1)}>Next</Button></div>
          </div>
        )}
      </div>

      {open && <Workflow q={open} onClose={() => setOpen(null)} onEdit={() => { setEditing(open); setOpen(null); }} onChange={(nq) => { setOpen(nq); reload(); }} />}
      {editing && <Editor initial={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />}
      {importing && <Importer onClose={() => setImporting(false)} onDone={() => { setImporting(false); reload(); }} />}
    </div>
  );
}

function Workflow({ q, onClose, onEdit, onChange }: { q: any; onClose: () => void; onEdit: () => void; onChange: (q: any) => void }) {
  const [correct, setCorrect] = useState<number | null>(q.correct_option);
  const [source, setSource] = useState("");
  const [notes, setNotes] = useState(q.review_notes ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const toast = useToast();
  const step = FLOW.findIndex((f) => f.s === q.status);

  async function go(target: string) {
    setBusy(target); setErr("");
    try {
      const nq = await api(`/admin-api/questions/${q.id}/transition`, { method: "POST", json: { status: target, correct_option: correct, source, notes } });
      toast({ tone: "success", title: `Moved to ${target.replace(/_/g, " ")}` });
      onChange(nq);
    } catch (e) { setErr(extractMessage((e as ApiError).data) || (e as Error).message); } finally { setBusy(null); }
  }

  return (
    <Modal open onClose={onClose} title={`Question #${q.id}`} className="sm:max-w-2xl">
      <ol className="mb-5 flex items-center gap-1 overflow-x-auto scrollbar-none text-xs font-semibold">
        {FLOW.map((f, i) => (
          <li key={f.s} className="flex shrink-0 items-center gap-1">
            <span className={cn("flex items-center gap-1 rounded-full px-2.5 py-1", i < step ? "bg-brand-100 text-brand-800" : i === step ? "bg-brand-600 text-white" : "bg-slate-100 text-muted")}>{i < step && <Check className="h-3 w-3" />}{f.label}</span>
            {i < FLOW.length - 1 && <ArrowRight className="h-3 w-3 text-slate-300" />}
          </li>
        ))}
      </ol>
      {q.status === "rejected" && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">Rejected: {q.review_notes}</p>}
      {q.passage_text && <p className="mb-3 text-sm text-muted">{q.passage_text}</p>}
      <Markdown className="font-semibold">{q.text}</Markdown>
      <div className="mt-4 space-y-2" role="radiogroup" aria-label="Correct option">
        {q.options.map((o: any) => (
          <button key={o.id} disabled={!["validated", "answer_verified"].includes(q.status)} onClick={() => setCorrect(o.id)}
            className={cn("flex w-full items-center gap-3 rounded-xl border-2 px-3 py-2 text-left text-sm", correct === o.id ? "border-brand-600 bg-brand-50" : "border-line")}>
            <span className="font-bold">{o.label}.</span><Markdown className="flex-1 [&_p]:my-0">{o.text}</Markdown>{correct === o.id && <ShieldCheck className="h-4 w-4 text-brand-600" />}
          </button>
        ))}
      </div>
      {q.answer_verified_by && <p className="mt-2 text-xs text-muted">Answer verified by {q.answer_verified_by}</p>}
      {q.explanation && <div className="mt-4 rounded-xl bg-canvas p-3 text-sm"><p className="text-xs font-bold uppercase text-muted">Explanation</p><Markdown>{q.explanation}</Markdown></div>}
      {q.is_ai_generated && <p className="mt-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-900">AI-generated. A person must verify the answer against an authoritative source before this can be published.</p>}

      {["validated", "answer_verified"].includes(q.status) && (
        <div className="mt-4"><Label>Verification source</Label><Input value={source} placeholder="e.g. WAEC syllabus 2025 / checked by Mr Adebayo" onChange={(e) => setSource(e.target.value)} /></div>
      )}
      <div className="mt-4"><Label>Review notes</Label><Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
      {err && <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{err}</p>}

      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button variant="ghost" onClick={onEdit}><Pencil className="h-4 w-4" /> Edit</Button>
        {q.status !== "rejected" && q.status !== "published" && <Button variant="ghost" onClick={() => go("rejected")} loading={busy === "rejected"}><X className="h-4 w-4" /> Reject</Button>}
        {(q.status === "published" || q.status === "rejected") && <Button variant="secondary" onClick={() => go("draft")} loading={busy === "draft"}>Move to draft</Button>}
        {q.status === "draft" && <Button onClick={() => go("validated")} loading={busy === "validated"}>Validate</Button>}
        {q.status === "validated" && <Button onClick={() => go("answer_verified")} disabled={!correct} loading={busy === "answer_verified"}><ShieldCheck className="h-4 w-4" /> Verify answer</Button>}
        {q.status === "answer_verified" && <Button onClick={() => go("in_review")} loading={busy === "in_review"}>Send to review</Button>}
        {q.status === "in_review" && <Button onClick={() => go("published")} loading={busy === "published"}>Publish</Button>}
      </div>
    </Modal>
  );
}

function Editor({ initial, onClose, onSaved }: { initial: any; onClose: () => void; onSaved: () => void }) {
  const { data: subjects } = useSWR<any>("/admin-api/subjects?page_size=100");
  const [v, setV] = useState<any>({ ...initial, steps: (initial.solution_steps ?? []).join("\n") });
  const { data: topics } = useSWR<any>(v.subject ? `/admin-api/topics?subject=${v.subject}&page_size=100` : null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const setOpt = (i: number, text: string) => setV({ ...v, options: v.options.map((o: any, j: number) => (j === i ? { ...o, text } : o)) });
  async function save() {
    setBusy(true); setErr("");
    const body = { subject: Number(v.subject), topic: v.topic ? Number(v.topic) : null, text: v.text, explanation: v.explanation ?? "", difficulty: Number(v.difficulty),
      exam_year: v.exam_year ? Number(v.exam_year) : null, source: v.source ?? "", is_official_past_question: !!v.is_official_past_question,
      solution_steps: (v.steps || "").split("\n").map((s: string) => s.trim()).filter(Boolean),
      options: v.options.filter((o: any) => o.text.trim()).map((o: any, i: number) => ({ label: "ABCDE"[i], text: o.text, order: i })) };
    try {
      if (initial.id) await api(`/admin-api/questions/${initial.id}`, { method: "PATCH", json: body });
      else await api("/admin-api/questions", { method: "POST", json: body });
      onSaved();
    } catch (e) { setErr(extractMessage((e as ApiError).data) || (e as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal open onClose={onClose} title={initial.id ? "Edit question" : "New question"} className="sm:max-w-2xl">
      {initial.id && initial.correct_option && <p className="mb-4 rounded-xl bg-amber-50 p-3 text-xs text-amber-900">Changing options removes the verified answer key and returns the question to draft.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <div><Label>Subject *</Label><Select value={v.subject ?? ""} onChange={(e) => setV({ ...v, subject: e.target.value, topic: "" })}><option value="">—</option>{subjects?.results?.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select></div>
        <div><Label>Topic</Label><Select value={v.topic ?? ""} onChange={(e) => setV({ ...v, topic: e.target.value })}><option value="">—</option>{topics?.results?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}</Select></div>
        <div className="sm:col-span-2"><Label>Question * <span className="font-normal text-muted">(Markdown, LaTeX with $…$)</span></Label><Textarea rows={3} value={v.text ?? ""} onChange={(e) => setV({ ...v, text: e.target.value })} /></div>
        {v.options.map((o: any, i: number) => (
          <div key={i}><Label>Option {"ABCDE"[i]}</Label><Input value={o.text} onChange={(e) => setOpt(i, e.target.value)} /></div>
        ))}
        <div className="sm:col-span-2"><Label>Explanation</Label><Textarea rows={3} value={v.explanation ?? ""} onChange={(e) => setV({ ...v, explanation: e.target.value })} /></div>
        <div className="sm:col-span-2"><Label>Solution steps <span className="font-normal text-muted">(one per line)</span></Label><Textarea rows={3} value={v.steps} onChange={(e) => setV({ ...v, steps: e.target.value })} /></div>
        <div><Label>Difficulty</Label><Select value={v.difficulty} onChange={(e) => setV({ ...v, difficulty: e.target.value })}><option value={1}>Easy</option><option value={2}>Medium</option><option value={3}>Hard</option></Select></div>
        <div><Label>Exam year</Label><Input type="number" value={v.exam_year ?? ""} onChange={(e) => setV({ ...v, exam_year: e.target.value })} /></div>
        <div className="sm:col-span-2"><Label>Source / licence</Label><Input value={v.source ?? ""} placeholder="Authorised source of this question" onChange={(e) => setV({ ...v, source: e.target.value })} /></div>
      </div>
      {v.options.length < 5 && <Button variant="ghost" size="sm" className="mt-2" onClick={() => setV({ ...v, options: [...v.options, { text: "" }] })}><Plus className="h-4 w-4" /> Add option</Button>}
      {v.options.length > 2 && <Button variant="ghost" size="sm" className="mt-2" onClick={() => setV({ ...v, options: v.options.slice(0, -1) })}><Trash2 className="h-4 w-4" /> Remove last option</Button>}
      {err && <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{err}</p>}
      <div className="mt-5 flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={save} loading={busy} disabled={!v.subject || !v.text}>Save as draft</Button></div>
    </Modal>
  );
}

const SAMPLE = `[
  {"subject_id": 2, "topic_id": null, "text": "What is 15% of 200?",
   "options": [{"label":"A","text":"20"},{"label":"B","text":"30"},{"label":"C","text":"35"},{"label":"D","text":"15"}],
   "explanation": "15/100 × 200 = 30", "difficulty": 1, "source": "Kwado original", "answer": "B"}
]`;

function Importer({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [text, setText] = useState(SAMPLE);
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  return (
    <Modal open onClose={onClose} title="Import questions" description="Paste a JSON array (max 1,000 rows). Imported questions start as drafts; any supplied answer is stored only as a suggestion until a person verifies it." className="sm:max-w-2xl">
      <Textarea rows={12} className="font-mono text-xs" value={text} onChange={(e) => setText(e.target.value)} />
      {err && <p className="mt-3 text-sm font-semibold text-red-700">{err}</p>}
      {res && <p className="mt-3 rounded-xl bg-brand-50 p-3 text-sm">Imported <b>{res.created}</b> question(s). {res.errors.length > 0 && <span className="text-red-700">{res.errors.length} row(s) failed: {res.errors.map((e: any) => `#${e.row}: ${e.error}`).join("; ")}</span>}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={res ? onDone : onClose}>{res ? "Done" : "Cancel"}</Button>
        <Button loading={busy} onClick={async () => {
          setErr(""); setBusy(true);
          try { const rows = JSON.parse(text); setRes(await api("/admin-api/questions/import", { method: "POST", json: { rows } })); }
          catch (e) { setErr(e instanceof SyntaxError ? "Invalid JSON." : (e as Error).message); } finally { setBusy(false); }
        }}>Import</Button>
      </div>
    </Modal>
  );
}
