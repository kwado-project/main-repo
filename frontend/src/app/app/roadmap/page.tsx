"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { AlertTriangle, BookOpen, BrainCircuit, CalendarDays, Check, Crown, Map, RefreshCw, RotateCcw, Sparkles, Swords, Undo2 } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { Badge, EmptyState, Progress, Skeleton, Tabs } from "@/components/ui/primitives";
import { ConfirmDialog, Modal } from "@/components/ui/overlay";
import { Markdown } from "@/components/ui/markdown";
import { CreditCoin, fireConfetti } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const KIND_ICON: Record<string, any> = { lesson: BookOpen, practice: Swords, revision: RotateCcw, mock: Crown, diagnostic: BrainCircuit };

export default function RoadmapPage() {
  const { data, mutate, isLoading } = useSWR<any>("/roadmaps/current");
  const [view, setView] = useState<"upcoming" | "all" | "done">("upcoming");
  const [open, setOpen] = useState<any>(null);
  const [regen, setRegen] = useState(false);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const groups = useMemo(() => {
    if (!data?.tasks) return [];
    const today = new Date().toISOString().slice(0, 10);
    let tasks = data.tasks as any[];
    if (view === "upcoming") tasks = tasks.filter((t) => t.status === "pending" && (t.date >= today || t.state === "overdue")).slice(0, 40);
    if (view === "done") tasks = tasks.filter((t) => t.status !== "pending");
    const m: Record<string, any[]> = {};
    tasks.forEach((t) => (m[t.date] ??= []).push(t));
    return Object.entries(m);
  }, [data, view]);

  async function setStatus(t: any, status: string) {
    const updated = await api(`/roadmaps/tasks/${t.id}`, { method: "POST", json: { status } });
    mutate({ ...data, tasks: data.tasks.map((x: any) => (x.id === t.id ? updated : x)),
      stats: { ...data.stats, completed: data.stats.completed + (status === "completed" ? 1 : t.status === "completed" ? -1 : 0) } }, { revalidate: true });
    if (status === "completed") fireConfetti();
    setOpen(null);
  }

  async function regenerate() {
    setBusy(true);
    try {
      await api("/roadmaps/generate", { method: "POST", json: {} });
      await mutate();
      toast({ tone: "success", title: "Roadmap regenerated", body: "Your plan now reflects your latest progress." });
      setRegen(false);
    } catch (e) {
      toast({ tone: "error", title: "Couldn't regenerate", body: (e as ApiError).message });
    } finally { setBusy(false); }
  }

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-40" /><Skeleton className="h-24" /><Skeleton className="h-24" /></div>;
  if (!data?.roadmap) {
    return (
      <div className="card">
        <EmptyState icon={Map} title="You don't have a roadmap yet" body="Generate a personalised day-by-day plan from your exam date, subjects and diagnostic results."
          action={<Button onClick={() => setRegen(true)}><Sparkles className="h-4 w-4" /> Generate my roadmap · {data?.cost ?? 15} credits</Button>} />
        <ConfirmDialog open={regen} onClose={() => setRegen(false)} onConfirm={regenerate} loading={busy} title="Generate roadmap?" confirmLabel={`Use ${data?.cost ?? 15} credits`}
          body="Credits are only charged if the AI coaching summary completes successfully." />
      </div>
    );
  }

  const r = data.roadmap;
  const pct = (data.stats.completed / Math.max(1, data.stats.total)) * 100;
  const todayStr = new Date().toISOString().slice(0, 10);

  return (
    <div>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-extrabold sm:text-3xl">Your study roadmap</h1>
          <p className="mt-1 text-muted">Version {r.version}{r.last_adapted_at ? " · adapted to your latest results" : ""}</p>
        </div>
        <Button variant="secondary" onClick={() => setRegen(true)}><RefreshCw className="h-4 w-4" /> Regenerate</Button>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        <div className="relative overflow-hidden rounded-2xl bg-ink p-6 text-white lg:col-span-2">
          <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-brand-600/30 blur-2xl" />
          <div className="relative grid gap-5 sm:grid-cols-3">
            <div><p className="text-sm text-white/60">Exam date</p><p className="mt-1 text-xl font-extrabold">{r.exam_date ? new Date(r.exam_date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "Not set"}</p></div>
            <div><p className="text-sm text-white/60">Tasks done</p><p className="mt-1 text-xl font-extrabold">{data.stats.completed} / {data.stats.total}</p></div>
            <div><p className="text-sm text-white/60">Overdue</p><p className={cn("mt-1 text-xl font-extrabold", data.stats.overdue && "text-amber-300")}>{data.stats.overdue}</p></div>
          </div>
          <Progress value={pct} className="relative mt-6 h-3 bg-white/10" />
        </div>
        <div className="card p-5">
          <p className="flex items-center gap-2 font-bold"><Sparkles className="h-4 w-4 text-brand-600" /> Coach summary</p>
          {r.ai_summary ? <Markdown className="mt-2 text-sm">{r.ai_summary}</Markdown> : <p className="mt-2 text-sm text-muted">{r.summary}</p>}
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between gap-3">
        <Tabs value={view} onChange={setView} tabs={[{ value: "upcoming", label: "Upcoming" }, { value: "all", label: "Timeline" }, { value: "done", label: "Completed" }]} />
        <div className="hidden items-center gap-3 text-xs font-semibold text-muted sm:flex">
          <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-brand-600" /> Done</span>
          <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-ink" /> Today</span>
          <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> Overdue</span>
        </div>
      </div>

      <div className="relative mt-6 space-y-6 before:absolute before:bottom-0 before:left-[27px] before:top-2 before:w-0.5 before:bg-line">
        {groups.length === 0 && <p className="pl-16 text-muted">Nothing here yet.</p>}
        {groups.map(([date, tasks]) => {
          const d = new Date(date);
          const isToday = date === todayStr;
          return (
            <section key={date} className="relative">
              <div className="flex items-center gap-4">
                <div className={cn("relative z-10 flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl text-center", isToday ? "bg-ink text-white" : "bg-white ring-1 ring-line")}>
                  <span className="text-[10px] font-bold uppercase leading-none">{d.toLocaleDateString("en-GB", { weekday: "short" })}</span>
                  <span className="text-lg font-extrabold leading-tight">{d.getDate()}</span>
                </div>
                <p className="font-bold">{isToday ? "Today" : d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}</p>
              </div>
              <div className="ml-[72px] mt-3 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2.5">
                {tasks.map((t: any, i: number) => {
                  const Icon = KIND_ICON[t.kind] ?? BookOpen;
                  return (
                    <motion.button key={t.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }} onClick={() => setOpen(t)}
                      className={cn("flex items-center gap-3 rounded-2xl border bg-white p-3.5 text-left transition hover:shadow-card",
                        t.status === "completed" ? "border-brand-200 bg-brand-50/50" : t.state === "overdue" ? "border-amber-300" : t.state === "current" ? "border-ink" : "border-line")}>
                      <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", t.status === "completed" ? "bg-brand-600 text-white" : t.kind === "mock" ? "bg-gold text-ink" : "bg-slate-100 text-slate-600")}>
                        {t.status === "completed" ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className={cn("truncate font-semibold", t.status === "completed" && "text-muted line-through")}>{t.title}</p>
                        <p className="truncate text-xs text-muted">{[t.subject?.name, `${t.minutes} min`].filter(Boolean).join(" · ")}</p>
                      </div>
                      {t.state === "overdue" && <Badge tone="amber"><AlertTriangle className="h-3 w-3" /> Overdue</Badge>}
                      {t.status === "pending" && t.state !== "overdue" && <Badge tone={t.priority === "high" ? "red" : t.priority === "medium" ? "amber" : "gray"} className="hidden sm:inline-flex">{t.priority}</Badge>}
                    </motion.button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>

      <Modal open={!!open} onClose={() => setOpen(null)} title={open?.title} description={open ? `${open.kind[0].toUpperCase() + open.kind.slice(1)} · ${open.minutes} minutes · ${open.priority} priority` : ""}>
        {open && (
          <div className="space-y-4">
            {open.description && <p className="text-[15px]">{open.description}</p>}
            <p className="flex items-center gap-2 text-sm text-muted"><CalendarDays className="h-4 w-4" /> {new Date(open.date).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Link href={taskHref(open)} className={buttonClass("primary", "lg")}>{open.kind === "lesson" ? "Open lesson" : open.kind === "mock" ? "Start mock exam" : "Start practice"}</Link>
              {open.status === "completed"
                ? <Button variant="secondary" size="lg" onClick={() => setStatus(open, "pending")}><Undo2 className="h-4 w-4" /> Mark not done</Button>
                : <Button variant="secondary" size="lg" onClick={() => setStatus(open, "completed")}><Check className="h-4 w-4" /> Mark complete</Button>}
            </div>
            {open.status === "pending" && <button onClick={() => setStatus(open, "skipped")} className="w-full text-sm font-semibold text-muted hover:text-ink">Skip this task</button>}
          </div>
        )}
      </Modal>
      <ConfirmDialog open={regen} onClose={() => setRegen(false)} onConfirm={regenerate} loading={busy} title="Regenerate your roadmap?" confirmLabel={`Use ${data.cost} credits`}
        body={<>A fresh plan will be built from your current mastery. Completed tasks stay in your history. <span className="inline-flex items-center gap-1 font-semibold text-ink"><CreditCoin size={14} /> {data.cost} credits</span>, charged only if the AI summary completes.</>} />
    </div>
  );
}

function taskHref(t: any) {
  if (t.kind === "lesson" && t.lesson_id) return `/app/lesson/${t.lesson_id}`;
  if (t.kind === "mock") return "/app/practice?kind=mock";
  if (t.kind === "diagnostic") return "/app/practice?kind=diagnostic";
  if (t.topic_id) return `/app/practice?kind=topic&subject=${t.subject?.id ?? ""}&topic=${t.topic_id}`;
  return "/app/practice";
}
