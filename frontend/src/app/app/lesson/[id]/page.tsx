"use client";
import Link from "next/link";
import { use, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR, { useSWRConfig } from "swr";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Bot, Check, Clock, Lightbulb, Sparkles, Target, X } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { Progress, Skeleton } from "@/components/ui/primitives";
import { Markdown } from "@/components/ui/markdown";
import { Flame, XPGem, fireConfetti } from "@/components/ui/fun";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function LessonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const { data: lesson, error } = useSWR<any>(`/learning/lessons/${id}`);
  const [i, setI] = useState(-1); // -1 = intro
  const [checks, setChecks] = useState<Record<number, number>>({});
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  if (error) return <div className="p-10 text-center">Lesson not found. <Link href="/app/learn" className="font-semibold text-brand-700">Back to learning</Link></div>;
  if (!lesson) return <div className="mx-auto max-w-2xl space-y-4 p-6"><Skeleton className="h-8 w-1/2" /><Skeleton className="h-64" /></div>;

  const blocks: any[] = lesson.content ?? [];
  const block = blocks[i];
  const isCheck = block?.type === "check";
  const answered = isCheck ? checks[i] !== undefined : true;
  const pct = i < 0 ? 0 : ((i + (answered ? 1 : 0.5)) / blocks.length) * 100;

  async function finish() {
    setBusy(true);
    try {
      const r = await api(`/learning/lessons/${id}/complete`, { method: "POST" });
      setResult(r);
      fireConfetti({ big: (r.badges?.length ?? 0) > 0 });
      mutate("/gamification/summary");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 border-b border-line bg-canvas/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-2xl items-center gap-4 px-4">
          <button onClick={() => router.back()} className="rounded-xl p-2 text-muted hover:bg-white hover:text-ink" aria-label="Exit lesson"><X className="h-6 w-6" /></button>
          <Progress value={result ? 100 : pct} className="h-3" animateIn={false} />
          <span className="flex shrink-0 items-center gap-1 text-sm font-bold text-brand-700"><XPGem size={18} />{lesson.xp_reward}</span>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-8">
        <AnimatePresence mode="wait">
          {result ? (
            <motion.div key="done" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="my-auto text-center">
              <motion.div initial={{ scale: 0, rotate: -30 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 200, damping: 12 }}
                className="mx-auto flex h-28 w-28 items-center justify-center rounded-[2rem] bg-brand-600 text-white shadow-glow"><Sparkles className="h-14 w-14" /></motion.div>
              <h1 className="mt-8 text-3xl font-extrabold">Lesson complete!</h1>
              <p className="mt-2 text-muted">{lesson.title}</p>
              <div className="mx-auto mt-8 grid max-w-sm grid-cols-2 gap-3">
                <div className="rounded-2xl border-2 border-brand-200 bg-white p-4">
                  <p className="text-xs font-bold uppercase text-brand-700">XP earned</p>
                  <p className="mt-1 flex items-center justify-center gap-1.5 text-3xl font-extrabold"><XPGem size={24} />+{result.xp_earned}</p>
                </div>
                <div className="rounded-2xl border-2 border-orange-200 bg-white p-4">
                  <p className="text-xs font-bold uppercase text-orange-600">Streak</p>
                  <p className="mt-1 flex items-center justify-center gap-1 text-3xl font-extrabold"><Flame size={28} />{result.streak}</p>
                </div>
              </div>
              {!result.first_time && <p className="mt-4 text-sm text-muted">You&apos;d already completed this lesson, so no extra XP this time.</p>}
              {result.badges?.map((b: any) => <p key={b.name} className="mt-4 font-bold text-brand-700">Badge unlocked: {b.name}!</p>)}
              <div className="mt-10 grid gap-3 sm:grid-cols-2">
                <Link href={`/app/practice?kind=topic&subject=${lesson.subject.id}&topic=${lesson.topic.id}`} className={buttonClass("primary", "lg")}>Practise this topic</Link>
                {lesson.next_lesson
                  ? <Link href={`/app/lesson/${lesson.next_lesson.id}`} className={buttonClass("secondary", "lg")}>Next lesson <ArrowRight className="h-5 w-5" /></Link>
                  : <Link href={`/app/learn/${lesson.subject.id}`} className={buttonClass("secondary", "lg")}>Back to path</Link>}
              </div>
            </motion.div>
          ) : i < 0 ? (
            <motion.div key="intro" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -30 }} className="my-auto">
              <p className="eyebrow">{lesson.subject.name} · {lesson.topic.name}</p>
              <h1 className="mt-3 text-3xl font-extrabold leading-tight sm:text-4xl">{lesson.title}</h1>
              <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50 p-5">
                <p className="flex items-center gap-2 text-sm font-bold text-brand-800"><Target className="h-4 w-4" /> Objective</p>
                <p className="mt-1.5 text-[15px]">{lesson.objective}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-3 text-sm font-semibold text-muted">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 ring-1 ring-line"><Clock className="h-4 w-4" /> {lesson.estimated_minutes} min</span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 ring-1 ring-line"><XPGem size={16} /> {lesson.xp_reward} XP</span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 ring-1 ring-line">{blocks.length} steps</span>
              </div>
            </motion.div>
          ) : (
            <motion.div key={i} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.25 }}>
              <LessonBlock block={block} picked={checks[i]} onPick={(o) => setChecks((c) => ({ ...c, [i]: o }))} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {!result && (
        <footer className="safe-bottom sticky bottom-0 border-t border-line bg-white">
          <div className="mx-auto flex max-w-2xl items-center justify-between gap-3 px-4 py-4">
            {i >= 0 ? <Link href={`/app/tutor?subject=${lesson.subject.id}&topic=${lesson.topic.id}&prompt=${encodeURIComponent(`I'm studying "${lesson.title}". Can you explain it another way?`)}`} className={buttonClass("ghost", "md")}><Bot className="h-5 w-5" /> <span className="hidden sm:inline">Ask tutor</span></Link> : <span />}
            {i < blocks.length - 1 ? (
              <Button size="lg" onClick={() => setI(i + 1)} disabled={!answered} className="min-w-[160px]">{i < 0 ? "Start lesson" : "Continue"} <ArrowRight className="h-5 w-5" /></Button>
            ) : (
              <Button size="lg" onClick={finish} loading={busy} disabled={!answered} className="min-w-[160px]">Finish lesson <Check className="h-5 w-5" /></Button>
            )}
          </div>
        </footer>
      )}
    </div>
  );
}

function LessonBlock({ block, picked, onPick }: { block: any; picked?: number; onPick: (i: number) => void }) {
  switch (block.type) {
    case "formula":
      return (
        <div className="rounded-3xl bg-ink p-6 text-white sm:p-8">
          {block.title && <p className="text-sm font-bold uppercase tracking-wider text-brand-400">{block.title}</p>}
          <Markdown className="mt-3 text-xl text-white [&_.katex]:text-2xl">{block.body}</Markdown>
        </div>
      );
    case "example":
      return (
        <div>
          <p className="eyebrow">Worked example</p>
          <Markdown className="mt-2 text-xl font-bold">{block.title}</Markdown>
          <ol className="mt-5 space-y-3">
            {block.steps.map((s: string, k: number) => (
              <motion.li key={k} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 + k * 0.25 }} className="card flex gap-4 p-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">{k + 1}</span>
                <Markdown className="pt-0.5">{s}</Markdown>
              </motion.li>
            ))}
          </ol>
        </div>
      );
    case "tip":
      return (
        <div className="rounded-3xl border-2 border-amber-200 bg-amber-50 p-6">
          <p className="flex items-center gap-2 font-bold text-amber-800"><Lightbulb className="h-5 w-5" /> Pro tip</p>
          <Markdown className="mt-2 text-lg">{block.body}</Markdown>
        </div>
      );
    case "table":
      return (
        <div>
          {block.title && <h2 className="mb-4 text-2xl font-extrabold">{block.title}</h2>}
          <div className="card divide-y divide-line">
            {block.rows.map((r: string[], k: number) => (
              <motion.div key={k} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: k * 0.08 }} className="grid grid-cols-[1fr_1.6fr] gap-4 p-4">
                <span className="font-bold text-brand-800">{r[0]}</span><span>{r[1]}</span>
              </motion.div>
            ))}
          </div>
        </div>
      );
    case "check": {
      const done = picked !== undefined;
      return (
        <div>
          <p className="eyebrow">Quick check</p>
          <Markdown className="mt-2 text-xl font-bold">{block.question}</Markdown>
          <div className="mt-5 grid gap-2.5">
            {block.options.map((o: string, k: number) => {
              const state = !done ? "idle" : k === block.answer ? "correct" : k === picked ? "wrong" : "dim";
              return (
                <motion.button key={k} disabled={done} onClick={() => onPick(k)} whileTap={!done ? { scale: 0.98 } : {}}
                  animate={state === "wrong" ? { x: [0, -6, 6, -4, 4, 0] } : {}}
                  className={cn("flex items-center gap-3 rounded-2xl border-2 bg-white px-4 py-3.5 text-left font-semibold transition",
                    state === "idle" && "border-line hover:border-brand-400", state === "correct" && "border-brand-500 bg-brand-50",
                    state === "wrong" && "border-red-400 bg-red-50", state === "dim" && "border-line opacity-50")}>
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-2 border-current/20 text-sm">{state === "correct" ? <Check className="h-4 w-4 text-brand-600" /> : state === "wrong" ? <X className="h-4 w-4 text-red-600" /> : "ABCD"[k]}</span>
                  <Markdown>{o}</Markdown>
                </motion.button>
              );
            })}
          </div>
          {done && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn("mt-4 rounded-2xl p-4", picked === block.answer ? "bg-brand-600 text-white" : "bg-ink text-white")}>
              <p className="font-bold">{picked === block.answer ? "Exactly right!" : "Good try — here's why"}</p>
              <Markdown className="mt-1 text-white/90">{block.explanation}</Markdown>
            </motion.div>
          )}
        </div>
      );
    }
    default:
      return (
        <div>
          {block.title && <h2 className="text-2xl font-extrabold">{block.title}</h2>}
          <Markdown className="mt-3 text-lg leading-8">{block.body}</Markdown>
        </div>
      );
  }
}
