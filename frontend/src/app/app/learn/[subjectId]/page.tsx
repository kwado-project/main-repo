"use client";
import Link from "next/link";
import { use, useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { ArrowLeft, BookOpen, Bot, Check, Crown, Lock, Star, Swords, Zap } from "lucide-react";
import { Badge, Progress, Skeleton, Tabs } from "@/components/ui/primitives";
import { buttonClass } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function SubjectPage({ params }: { params: Promise<{ subjectId: string }> }) {
  const { subjectId } = use(params);
  const [tab, setTab] = useState<"path" | "topics">("path");
  const { data: path } = useSWR<any>(`/learning/paths/${subjectId}`);
  const { data: topics } = useSWR<any[]>(`/assessments/subjects/${subjectId}/topics`);
  const { data: subjects } = useSWR<any[]>("/subjects");
  const subject = subjects?.find((s) => String(s.id) === subjectId);

  return (
    <div>
      <Link href="/app/learn" className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" /> All subjects</Link>
      <div className="mt-3 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-2xl font-extrabold sm:text-3xl">{subject?.name ?? "…"}</h1>
          {path?.total ? <p className="mt-1 text-muted">{path.completed} of {path.total} steps complete</p> : null}
        </div>
        <Tabs value={tab} onChange={setTab} tabs={[{ value: "path", label: "Learning path" }, { value: "topics", label: "Topics" }]} />
      </div>
      {path?.total ? <Progress value={(path.completed / path.total) * 100} className="mt-4 h-3" /> : null}

      {tab === "path" ? <PathView path={path} subjectId={subjectId} /> : <TopicsView topics={topics} subjectId={subjectId} />}
    </div>
  );
}

function PathView({ path, subjectId }: { path: any; subjectId: string }) {
  if (!path) return <div className="mt-8 space-y-6">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="mx-auto h-20 w-20 rounded-full" />)}</div>;
  if (!path.nodes.length) return <p className="mt-8 text-muted">The learning path for this subject is coming soon. Use the Topics tab to practise now.</p>;
  return (
    <div className="relative mx-auto mt-10 max-w-md pb-10">
      {path.nodes.map((n: any, i: number) => {
        const offset = Math.round(Math.sin(i * 0.9) * 60);
        const href = n.state === "locked" ? undefined : n.kind === "lesson" ? `/app/lesson/${n.lesson_id}` : `/app/practice?kind=challenge&subject=${subjectId}&topic=${n.topic_id}&auto=1`;
        const Icon = n.state === "completed" ? Check : n.state === "locked" ? Lock : n.kind === "boss" ? Crown : n.kind === "challenge" ? Swords : BookOpen;
        const inner = (
          <div style={{ transform: `translateX(${offset}px)` }}>
          <motion.div initial={{ opacity: 0, scale: 0.6 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ type: "spring", stiffness: 260, damping: 18 }}
            className="flex flex-col items-center">
            <div className="relative">
              {n.state === "current" && (
                <>
                  <motion.span className="absolute inset-0 rounded-full bg-brand-400" animate={{ scale: [1, 1.35], opacity: [0.5, 0] }} transition={{ duration: 1.6, repeat: Infinity }} />
                  <motion.span initial={{ y: 6, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="absolute -top-11 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-xl bg-ink px-3 py-1.5 text-xs font-bold text-white shadow-lift">
                    Start here<span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 bg-ink" />
                  </motion.span>
                </>
              )}
              <span className={cn("relative flex items-center justify-center rounded-full border-b-[6px] transition active:translate-y-1 active:border-b-2",
                n.kind === "boss" ? "h-24 w-24" : "h-[76px] w-[76px]",
                n.state === "completed" ? "border-brand-800 bg-brand-600 text-white" :
                n.state === "current" ? (n.kind === "boss" ? "border-amber-700 bg-gold text-ink" : "border-brand-800 bg-brand-500 text-white") :
                "border-slate-300 bg-slate-200 text-slate-400")}>
                <Icon className={n.kind === "boss" ? "h-10 w-10" : "h-8 w-8"} strokeWidth={2.4} />
                {n.state === "completed" && <Star className="absolute -right-1 -top-1 h-6 w-6 fill-gold text-gold" />}
              </span>
            </div>
            <p className={cn("mt-2 max-w-[180px] text-center text-sm font-bold", n.state === "locked" && "text-slate-400")}>{n.title}</p>
            <p className="text-xs text-muted">{n.kind === "lesson" ? `Lesson · ${n.estimated_minutes} min` : n.kind === "boss" ? `Boss · pass ${n.pass_mark}%` : `Challenge · pass ${n.pass_mark}%`}</p>
          </motion.div>
          </div>
        );
        return (
          <div key={n.id} className="relative flex justify-center py-5">
            {href ? <Link href={href} aria-label={`${n.title} (${n.state})`}>{inner}</Link> : <div aria-label={`${n.title} (locked)`}>{inner}</div>}
          </div>
        );
      })}
      <div className="mt-4 flex justify-center"><Badge tone="dark"><Zap className="h-3 w-3" /> Challenges use hearts — 3 mistakes and you&apos;re out</Badge></div>
    </div>
  );
}

function TopicsView({ topics, subjectId }: { topics?: any[]; subjectId: string }) {
  if (!topics) return <div className="mt-6 space-y-3">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>;
  return (
    <div className="mt-6 grid gap-3">
      {topics.map((t, i) => (
        <motion.div key={t.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }} className="card flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2"><p className="font-bold">{t.name}</p>{t.mastery !== null && t.mastery < 50 && <Badge tone="amber">Needs work</Badge>}{t.mastery >= 85 && <Badge>Mastered</Badge>}</div>
            <div className="mt-2 flex items-center gap-3">
              <Progress value={t.mastery ?? 0} className="h-2 max-w-xs" />
              <span className="text-xs font-semibold text-muted">{t.mastery === null ? "Not started" : `${t.mastery}% mastery`} · {t.lessons} lesson{t.lessons === 1 ? "" : "s"}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href={`/app/tutor?subject=${subjectId}&topic=${t.id}&prompt=${encodeURIComponent(`Teach me ${t.name} step by step.`)}`} className={buttonClass("secondary", "sm")}><Bot className="h-4 w-4" /> Explain</Link>
            <Link href={`/app/practice?kind=topic&subject=${subjectId}&topic=${t.id}`} className={buttonClass("primary", "sm")}><Swords className="h-4 w-4" /> Practise</Link>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
