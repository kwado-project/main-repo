"use client";
import { useState } from "react";
import useSWR from "swr";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  AlertTriangle, CheckCircle2, Download, ExternalLink, FileSearch, Globe, Play, Plus, RefreshCw, ShieldCheck, ShieldQuestion, XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, EmptyState, Input, Label, Select, Skeleton, Tabs, Textarea } from "@/components/ui/primitives";
import { Modal } from "@/components/ui/overlay";
import { Markdown } from "@/components/ui/markdown";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, extractMessage, rawFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const PERM: Record<string, { label: string; tone: any }> = {
  unknown: { label: "Not reviewed", tone: "gray" }, needs_review: { label: "Needs review", tone: "amber" },
  terms_prohibit: { label: "Terms prohibit", tone: "red" }, robots_disallow: { label: "robots.txt blocks", tone: "red" },
  permitted: { label: "Permitted", tone: "green" }, open_license: { label: "Open licence", tone: "green" }, denied: { label: "Denied", tone: "red" },
};
const CELL: Record<string, string> = {
  verified: "bg-brand-600 text-white", extracted: "bg-brand-200 text-brand-900", sources_found: "bg-amber-200 text-amber-900",
  searching: "bg-sky-200 text-sky-900", unavailable: "bg-slate-300 text-slate-600", missing: "bg-slate-100 text-slate-400",
};

export default function ResearchDashboard() {
  const { me } = useAuth();
  const isAdmin = me?.role === "admin";
  const { data, mutate, isLoading } = useSWR<any>("/admin-api/research/overview", { refreshInterval: 30000 });
  const [tab, setTab] = useState<"review" | "sources" | "missing" | "jobs">("review");
  const [seedOpen, setSeedOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function runCycle() {
    setBusy(true);
    try {
      await api("/admin-api/research/run", { method: "POST", json: { action: "cycle" } });
      toast({ tone: "success", title: "Research cycle queued", body: "It runs on the research worker; this page refreshes every 30 seconds." });
      setTimeout(() => mutate(), 3000);
    } catch (e) {
      toast({ tone: "error", title: "Couldn't start", body: (e as ApiError).message });
    } finally { setBusy(false); }
  }

  async function exportJson() {
    const res = await rawFetch("/admin-api/research/questions/export");
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `jamb-past-questions-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const t = data?.totals;
  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-2xl font-extrabold">Past-question research</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">JAMB UTME {data?.years?.[0] ?? 2000}–{data?.years?.at(-1) ?? 2026}. Questions are only extracted from sources with recorded permission or an open licence, and stay here until a person verifies them and they are promoted to the question bank.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={exportJson}><Download className="h-4 w-4" /> Export JSON</Button>
          {isAdmin && <Button variant="secondary" onClick={() => setSeedOpen(true)}><Plus className="h-4 w-4" /> Add seed site</Button>}
          {isAdmin && <Button onClick={runCycle} loading={busy}><Play className="h-4 w-4" /> Run research cycle</Button>}
        </div>
      </div>

      {isLoading || !t ? <Skeleton className="h-40" /> : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
          {[
            ["Questions collected", t.questions, "unique; duplicates excluded"],
            ["Verified", t.verified, "by a person"],
            ["Subjects covered", `${t.subjects_covered}/${t.subjects_total}`, "with ≥1 question"],
            ["Years covered", `${t.years_covered}/${t.years_total}`, "with ≥1 question"],
            ["Subject–year cells", `${t.cells_with_questions}/${t.cells_total}`, `${t.cells_missing} missing`],
            ["Awaiting verification", t.awaiting_human_verification, `${t.needs_review} flagged`],
            ["Awaiting copyright", t.awaiting_copyright_clearance, "questions"],
            ["Sources discovered", t.sources_discovered, `${t.sources_processed} processed`],
            ["Sources to review", t.sources_awaiting_permission_review, "permission decisions"],
            ["Documents found", t.documents_discovered, `${t.documents_extracted} extracted · ${t.documents_blocked} blocked`],
            ["Duplicates found", t.duplicates_found, "across sources"],
            ["Failed jobs", t.failed_jobs, "retried automatically"],
          ].map(([l, v, s]) => (
            <div key={l as string} className="card p-4">
              <p className="text-xs font-semibold text-muted">{l}</p>
              <p className="mt-1 text-2xl font-extrabold tabular-nums">{v}</p>
              <p className="text-[11px] text-muted">{s}</p>
            </div>
          ))}
        </div>
      )}

      {data && <CoverageMatrix data={data} />}

      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="Questions per subject" rows={data.per_subject.filter((r: any) => r.questions > 0)} x="subject" />
          <ChartCard title="Questions per year" rows={data.per_year} x="year" />
        </div>
      )}

      <div>
        <Tabs value={tab} onChange={setTab} tabs={[{ value: "review", label: "Review queue" }, { value: "sources", label: "Sources & permissions" },
          { value: "missing", label: `Missing (${t?.cells_missing ?? 0})` }, ...(isAdmin ? [{ value: "jobs" as const, label: "Failed jobs" }] : [])]} />
        <div className="mt-4">
          {tab === "review" && <ReviewQueue onChange={() => mutate()} />}
          {tab === "sources" && <Sources isAdmin={isAdmin} onChange={() => mutate()} />}
          {tab === "missing" && <Missing rows={data?.missing ?? []} />}
          {tab === "jobs" && <Jobs />}
        </div>
      </div>
      <SeedModal open={seedOpen} onClose={() => setSeedOpen(false)} />
    </div>
  );
}

function CoverageMatrix({ data }: { data: any }) {
  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-bold">Coverage matrix</h2>
        <div className="flex flex-wrap gap-3 text-xs text-muted">
          {[["verified", "Verified"], ["extracted", "Extracted"], ["sources_found", "Sources found"], ["searching", "Searching"], ["unavailable", "Not found"], ["missing", "Not searched"]].map(([k, l]) => (
            <span key={k} className="flex items-center gap-1"><span className={cn("h-3 w-3 rounded", CELL[k])} />{l}</span>
          ))}
        </div>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="border-separate border-spacing-0.5 text-[11px]">
          <thead>
            <tr><th className="sticky left-0 z-10 bg-white pr-2 text-left font-semibold">Subject</th>{data.years.map((y: number) => <th key={y} className="w-9 font-semibold text-muted">{String(y).slice(2)}</th>)}</tr>
          </thead>
          <tbody>
            {data.matrix.map((row: any) => (
              <tr key={row.subject_id}>
                <td className="sticky left-0 z-10 max-w-[180px] truncate bg-white pr-2 font-semibold">{row.subject}</td>
                {row.cells.map((c: any) => (
                  <td key={c.year} title={`${row.subject} ${c.year}: ${c.status.replace("_", " ")} · ${c.questions ?? 0} questions (${c.verified ?? 0} verified) · ${c.documents ?? 0} documents · searched ${c.searches ?? 0}×`}
                    className={cn("h-7 w-9 rounded text-center font-bold tabular-nums", CELL[c.status] ?? CELL.missing)}>
                    {c.questions ? c.questions : ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.matrix.length === 0 && <p className="mt-3 text-sm text-muted">No matrix yet. Run a research cycle to create it.</p>}
    </section>
  );
}

function ChartCard({ title, rows, x }: { title: string; rows: any[]; x: string }) {
  return (
    <section className="card p-5">
      <h2 className="font-bold">{title}</h2>
      <div className="mt-3 h-60">
        {rows.length === 0 ? <p className="flex h-full items-center justify-center text-sm text-muted">No questions yet</p> : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ left: -16 }}>
              <XAxis dataKey={x} tick={{ fontSize: 10 }} interval={x === "subject" ? 0 : "preserveStartEnd"} angle={x === "subject" ? -30 : 0}
                textAnchor={x === "subject" ? "end" : "middle"} height={x === "subject" ? 70 : 24}
                tickFormatter={x === "year" ? (y) => `'${String(y).slice(2)}` : undefined} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 12 }} />
              <Bar dataKey="questions" fill="#86EFAC" radius={[4, 4, 0, 0]} />
              <Bar dataKey="verified" fill="#16A34A" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}

function ReviewQueue({ onChange }: { onChange: () => void }) {
  const [status, setStatus] = useState("awaiting");
  const { data, mutate } = useSWR<any>(`/admin-api/research/questions?${status === "awaiting" ? "awaiting=1" : `verification_status=${status}`}&page_size=10`);
  const reload = () => { mutate(); onChange(); };
  return (
    <div>
      <Select className="mb-3 sm:w-64" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
        <option value="awaiting">Awaiting a person (flagged first)</option><option value="needs_review">Flagged for review</option><option value="auto_checked">Passed automatic checks</option>
        <option value="unverified">Not yet checked</option><option value="verified">Verified</option><option value="rejected">Rejected</option>
      </Select>
      {!data ? <Skeleton className="h-40" /> : data.results.length === 0 ? (
        <div className="card"><EmptyState icon={CheckCircle2} title="Nothing here" body="Questions appear once permitted sources have been extracted." /></div>
      ) : (
        <div className="space-y-3">{data.results.map((q: any) => <ReviewCard key={q.id} q={q} onDone={reload} />)}</div>
      )}
      {data?.count > 10 && <p className="mt-3 text-sm text-muted">Showing 10 of {data.count}. Decide on these to see more.</p>}
    </div>
  );
}

function ReviewCard({ q, onDone }: { q: any; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const { data: detail } = useSWR<any>(open ? `/admin-api/research/questions/${q.id}` : null);
  const [answer, setAnswer] = useState(q.answers.find((a: any) => a.origin === "source")?.label ?? "");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const toast = useToast();
  const sourceAnswer = q.answers.find((a: any) => a.origin === "source")?.label;
  const aiAnswer = q.answers.find((a: any) => a.origin === "ai");

  async function act(kind: "verify" | "reject" | "promote") {
    setBusy(kind);
    try {
      const body = kind === "verify" ? { answer: answer && answer !== sourceAnswer ? answer : undefined, note: "" } : kind === "reject" ? { reason } : {};
      const r = await api<any>(`/admin-api/research/questions/${q.id}/${kind}`, { method: "POST", json: body });
      toast({ tone: "success", title: kind === "promote" ? `Added to the question bank as draft #${r.question_bank_id}` : kind === "verify" ? "Verified" : "Rejected" });
      onDone();
    } catch (e) {
      toast({ tone: "error", title: "Couldn't save", body: extractMessage((e as ApiError).data) || (e as Error).message });
    } finally { setBusy(null); }
  }

  return (
    <article className="card p-5">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge tone="dark">{q.subject_name ?? "No subject"} · {q.year ?? "no year"} · Q{q.question_number}</Badge>
        <Badge tone={q.rights_status === "cleared" ? "green" : "red"}>{q.rights_status.replace("_", " ")}</Badge>
        <Badge tone="gray">{q.extraction_method} · confidence {Math.round(q.extraction_confidence * 100)}%</Badge>
        <a href={q.source_url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 font-semibold text-brand-700">{q.source_domain}{q.page_number ? ` · p.${q.page_number}` : ""} <ExternalLink className="h-3 w-3" /></a>
      </div>
      {q.passage && <p className="mt-3 rounded-xl bg-canvas p-3 text-sm text-muted">{q.passage}</p>}
      <Markdown className="mt-3 font-semibold">{q.text}</Markdown>
      <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
        {Object.entries(q.options).map(([k, v]: any) => (
          <button key={k} onClick={() => setAnswer(k)} className={cn("flex gap-2 rounded-xl border-2 px-3 py-2 text-left text-sm", answer === k ? "border-brand-600 bg-brand-50" : "border-line")}>
            <b>{k}.</b><Markdown className="[&_p]:my-0">{v}</Markdown>
            {k === sourceAnswer && <Badge className="ml-auto shrink-0">source key</Badge>}
            {k === aiAnswer?.label && <Badge tone="blue" className="shrink-0">AI view</Badge>}
          </button>
        ))}
      </div>
      {q.flags.length > 0 && <p className="mt-3 flex items-start gap-1.5 text-xs text-amber-800"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{q.flags.join(" · ")}</p>}
      <button onClick={() => setOpen(!open)} className="mt-2 text-xs font-semibold text-brand-700">{open ? "Hide" : "Show"} check results</button>
      {open && detail && (
        <ul className="mt-2 space-y-1 text-xs">
          {detail.verifications.map((v: any, i: number) => (
            <li key={i} className="flex gap-2"><Badge tone={v.result === "pass" ? "green" : v.result === "fail" ? "red" : v.result === "warn" ? "amber" : "gray"}>{v.result}</Badge>
              <span className="font-semibold">{v.check}</span><span className="text-muted">{v.details?.reason ?? ""}</span></li>
          ))}
        </ul>
      )}
      {q.verification_status !== "verified" && q.verification_status !== "rejected" ? (
        <div className="mt-4 flex flex-col gap-2 border-t border-line pt-4 sm:flex-row sm:items-center">
          <p className="text-xs text-muted sm:flex-1">Select the correct option above if the source key is wrong or missing, then verify.</p>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (to reject)" className="h-10 sm:w-56" />
          <Button size="sm" variant="secondary" onClick={() => act("reject")} loading={busy === "reject"} disabled={!reason.trim()}><XCircle className="h-4 w-4" /> Reject</Button>
          <Button size="sm" onClick={() => act("verify")} loading={busy === "verify"} disabled={!answer}><CheckCircle2 className="h-4 w-4" /> Verify{answer ? ` (${answer})` : ""}</Button>
        </div>
      ) : q.verification_status === "verified" && !q.promoted_question ? (
        <div className="mt-4 flex justify-end border-t border-line pt-4">
          <Button size="sm" onClick={() => act("promote")} loading={busy === "promote"} disabled={q.rights_status !== "cleared"}>Promote to question bank</Button>
        </div>
      ) : q.promoted_question ? <p className="mt-3 text-xs font-semibold text-brand-700">In the question bank as draft #{q.promoted_question}</p> : null}
    </article>
  );
}

function Sources({ isAdmin, onChange }: { isAdmin: boolean; onChange: () => void }) {
  const [filter, setFilter] = useState("");
  const { data, mutate } = useSWR<any>(`/admin-api/research/sources?page_size=50${filter ? `&permission_status=${filter}` : ""}`);
  const [pick, setPick] = useState<any>(null);
  return (
    <div>
      <Select className="mb-3 sm:w-64" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Permission">
        <option value="">All sources</option>{Object.entries(PERM).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
      </Select>
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-wider text-muted">
            <tr><th className="px-4 py-3">Source</th><th className="px-4 py-3">Permission</th><th className="px-4 py-3">Documents</th><th className="px-4 py-3">Questions</th><th className="px-4 py-3">Terms</th><th className="px-4 py-3" /></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {!data && <tr><td colSpan={6} className="p-4"><Skeleton className="h-8" /></td></tr>}
            {data?.results?.length === 0 && <tr><td colSpan={6}><EmptyState icon={Globe} title="No sources yet" body="Add a seed site or configure a search provider, then run a cycle." /></td></tr>}
            {data?.results?.map((s: any) => (
              <tr key={s.id}>
                <td className="px-4 py-3"><a href={s.homepage || `https://${s.domain}`} target="_blank" rel="noopener noreferrer" className="font-semibold hover:underline">{s.domain}</a>
                  <p className="text-xs text-muted">{s.is_seed ? "seed" : s.discovered_via} · {s.years_seen?.length ?? 0} years · {s.subjects_seen?.length ?? 0} subjects</p></td>
                <td className="px-4 py-3"><Badge tone={PERM[s.permission_status]?.tone}>{PERM[s.permission_status]?.label ?? s.permission_status}</Badge>{s.license_name && <p className="mt-1 text-xs text-muted">{s.license_name}</p>}</td>
                <td className="px-4 py-3 tabular-nums">{s.documents}</td>
                <td className="px-4 py-3 tabular-nums">{s.questions}</td>
                <td className="px-4 py-3 text-xs">{s.terms_url ? <a className="text-brand-700 hover:underline" href={s.terms_url} target="_blank" rel="noopener noreferrer">Terms</a> : "—"}
                  {s.terms_flags?.length > 0 && <p className="mt-1 max-w-[220px] text-red-700">“{s.terms_flags[0]}”</p>}</td>
                <td className="px-4 py-3 text-right">{isAdmin && <Button size="sm" variant="secondary" onClick={() => setPick(s)}><ShieldCheck className="h-4 w-4" /> Permission</Button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pick && <PermissionModal source={pick} onClose={() => setPick(null)} onSaved={() => { setPick(null); mutate(); onChange(); }} />}
    </div>
  );
}

function PermissionModal({ source, onClose, onSaved }: { source: any; onClose: () => void; onSaved: () => void }) {
  const [status, setStatus] = useState("permitted");
  const [evidence, setEvidence] = useState("");
  const [scope, setScope] = useState("");
  const [licence, setLicence] = useState(source.license_name || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const toast = useToast();
  async function save() {
    setBusy(true); setErr("");
    try {
      await api(`/admin-api/research/sources/${source.id}/permission`, { method: "POST", json: { status, evidence, scope, license_name: licence } });
      toast({ tone: "success", title: "Decision recorded" });
      onSaved();
    } catch (e) { setErr(extractMessage((e as ApiError).data)); } finally { setBusy(false); }
  }
  async function recheck() {
    await api(`/admin-api/research/sources/${source.id}/check`, { method: "POST" });
    toast({ tone: "info", title: "robots.txt and terms re-checked" });
    onSaved();
  }
  return (
    <Modal open onClose={onClose} title={`Copyright decision · ${source.domain}`} className="sm:max-w-xl">
      <p className="text-sm text-muted">Only mark a source permitted with written permission from the rights holder, or a licence that clearly allows storing and showing its questions to your students. JAMB past questions are generally JAMB&apos;s copyright, whoever hosts them.</p>
      {source.terms_flags?.length > 0 && <p className="mt-3 flex gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800"><ShieldQuestion className="h-4 w-4 shrink-0" />The site&apos;s terms say: “{source.terms_flags.join("”, “")}”</p>}
      <div className="mt-4 grid gap-4">
        <div><Label>Decision</Label>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="permitted">Permitted: written permission received</option><option value="open_license">Open licence that allows our use</option>
            <option value="requested">Permission requested: waiting</option><option value="denied">Denied: do not use</option>
          </Select></div>
        {(status === "permitted" || status === "open_license") && <>
          <div><Label>Evidence (required)</Label><Textarea rows={3} value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="Paste the permission email or licence text, or link to the signed agreement" /></div>
          <div><Label>Scope</Label><Input value={scope} onChange={(e) => setScope(e.target.value)} placeholder="e.g. All JAMB past questions 2000–2026, for display to Kwado students" /></div>
          {status === "open_license" && <div><Label>Licence</Label><Input value={licence} onChange={(e) => setLicence(e.target.value)} placeholder="e.g. CC BY 4.0" /></div>}
        </>}
      </div>
      {err && <p className="mt-3 text-sm font-semibold text-red-600">{err}</p>}
      <div className="mt-6 flex flex-wrap justify-between gap-2">
        <Button variant="ghost" onClick={recheck}><RefreshCw className="h-4 w-4" /> Re-check robots &amp; terms</Button>
        <Button onClick={save} loading={busy}>Record decision</Button>
      </div>
    </Modal>
  );
}

function Missing({ rows }: { rows: any[] }) {
  const [subject, setSubject] = useState("");
  const subjects = Array.from(new Set(rows.map((r) => r.subject)));
  const shown = rows.filter((r) => !subject || r.subject === subject);
  return (
    <div>
      <Select className="mb-3 sm:w-64" value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Subject">
        <option value="">All subjects ({rows.length})</option>{subjects.map((s) => <option key={s} value={s}>{s}</option>)}
      </Select>
      <div className="card grid gap-x-6 p-4 sm:grid-cols-2 lg:grid-cols-3">
        {shown.slice(0, 300).map((r) => (
          <div key={`${r.subject}-${r.year}`} className="flex justify-between border-b border-dashed border-line py-2 text-sm">
            <span>{r.subject} <b>{r.year}</b></span><span className="text-xs text-muted">{r.status.replace("_", " ")}</span>
          </div>
        ))}
        {shown.length === 0 && <p className="text-sm text-muted">No gaps.</p>}
      </div>
    </div>
  );
}

function Jobs() {
  const { data } = useSWR<any[]>("/admin-api/research/jobs?status=failed");
  if (!data) return <Skeleton className="h-24" />;
  if (!data.length) return <div className="card"><EmptyState icon={FileSearch} title="No failed jobs" /></div>;
  return (
    <div className="card divide-y divide-line">
      {data.map((j) => (
        <div key={j.id} className="p-4 text-sm">
          <p className="font-semibold">{j.kind} · attempt {j.attempts} · {j.document ?? j.source ?? j.key}</p>
          <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap text-xs text-red-700">{j.error}</pre>
        </div>
      ))}
    </div>
  );
}

function SeedModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  return (
    <Modal open={open} onClose={onClose} title="Add a seed site" description="The next cycle checks its robots.txt and terms, then follows its links to find past-question pages (metadata only until you grant permission).">
      <Label>Website URL</Label><Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/" />
      <Label className="mt-4">Name (optional)</Label><Input value={name} onChange={(e) => setName(e.target.value)} />
      <Button className="mt-5 w-full" loading={busy} disabled={!url} onClick={async () => {
        setBusy(true);
        try { await api("/admin-api/research/seeds", { method: "POST", json: { url, name } }); toast({ tone: "success", title: "Seed added" }); setUrl(""); setName(""); onClose(); }
        catch (e) { toast({ tone: "error", title: "Couldn't add", body: extractMessage((e as ApiError).data) }); } finally { setBusy(false); }
      }}>Add seed</Button>
    </Modal>
  );
}
