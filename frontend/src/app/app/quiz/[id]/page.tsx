"use client";
import Link from "next/link";
import { Suspense, use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSWRConfig } from "swr";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft, ArrowRight, BookOpenText, Bot, Check, CheckCircle2, ChevronDown, Clock, Flag, Grid3x3, Heart, RotateCcw,
  Swords, Target, Timer, X, XCircle,
} from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { Badge, CountUp, Progress, Ring, Skeleton } from "@/components/ui/primitives";
import { ConfirmDialog, Drawer } from "@/components/ui/overlay";
import { Markdown } from "@/components/ui/markdown";
import { XPGem, fireConfetti } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { Attempt, QuizQuestion } from "@/lib/types";
import { cn, fmtDuration } from "@/lib/utils";

export default function QuizPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <Suspense><Quiz id={id} /></Suspense>;
}

function Quiz({ id }: { id: string }) {
  const router = useRouter();
  const search = useSearchParams();
  const toast = useToast();
  const { mutate } = useSWRConfig();
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [pending, setPending] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [confirmExit, setConfirmExit] = useState(false);
  const [palette, setPalette] = useState(false);
  const shownAt = useRef(Date.now());

  useEffect(() => {
    api<Attempt>(`/assessments/attempts/${id}`).then(setAttempt).catch((e: ApiError) => setError(e.status === 404 ? "This quiz doesn't exist." : e.message));
  }, [id]);

  useEffect(() => {
    shownAt.current = Date.now();
    setPending(null);
  }, [idx]);

  const q = attempt?.questions[idx];
  const practice = attempt?.mode === "practice";
  const submitted = attempt?.status === "submitted";
  const answeredCount = attempt?.questions.filter((x) => x.answered).length ?? 0;

  const updateQuestion = (nq: QuizQuestion) =>
    setAttempt((a) => a && { ...a, questions: a.questions.map((x) => (x.id === nq.id ? { ...x, ...nq } : x)) });

  async function choose(optionId: number) {
    if (!attempt || !q || submitted) return;
    if (practice) {
      if (q.answered) return;
      setPending(optionId);
      return;
    }
    // exam mode: save immediately, can change until submit
    updateQuestion({ ...q, selected_option: optionId, answered: true });
    try {
      await api(`/assessments/attempts/${id}/answer`, { method: "POST", json: { question: q.id, option: optionId, time_spent: Math.round((Date.now() - shownAt.current) / 1000) } });
    } catch (e) {
      toast({ tone: "error", title: "Answer not saved", body: (e as ApiError).message });
    }
  }

  async function check() {
    if (!q || pending === null) return;
    setSaving(true);
    try {
      const r = await api<{ question: QuizQuestion; hearts_remaining: number }>(`/assessments/attempts/${id}/answer`, {
        method: "POST", json: { question: q.id, option: pending, time_spent: Math.round((Date.now() - shownAt.current) / 1000) },
      });
      updateQuestion(r.question);
      setAttempt((a) => a && { ...a, hearts_remaining: r.hearts_remaining });
      setPending(null);
    } catch (e) {
      toast({ tone: "error", title: "Couldn't check answer", body: (e as ApiError).message });
    } finally {
      setSaving(false);
    }
  }

  async function toggleFlag() {
    if (!q) return;
    const flagged = !q.flagged;
    updateQuestion({ ...q, flagged });
    await api(`/assessments/attempts/${id}/flag`, { method: "POST", json: { question: q.id, flagged } }).catch(() => {});
  }

  const submit = useCallback(async () => {
    setSubmitting(true);
    try {
      const r = await api<Attempt>(`/assessments/attempts/${id}/submit`, { method: "POST" });
      setAttempt(r);
      setConfirmSubmit(false);
      mutate("/gamification/summary"); mutate("/gamification/missions"); mutate("/assessments/progress"); mutate("/learning/continue");
      if (Number(r.score_percent) >= 70) fireConfetti({ big: Number(r.score_percent) === 100 });
      window.scrollTo({ top: 0 });
    } catch (e) {
      toast({ tone: "error", title: "Submit failed", body: (e as ApiError).message });
    } finally {
      setSubmitting(false);
    }
  }, [id, mutate, toast]);

  // keyboard shortcuts: 1-4 / A-D choose, Enter check/next, arrows navigate
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (!q || submitted || (e.target as HTMLElement)?.tagName === "INPUT") return;
      const k = e.key.toLowerCase();
      const n = "1234".indexOf(k) >= 0 ? "1234".indexOf(k) : "abcd".indexOf(k);
      if (n >= 0 && q.options[n]) choose(q.options[n].id);
      if (e.key === "Enter") {
        if (practice && pending !== null) check();
        else if (practice && q.answered && idx < (attempt?.questions.length ?? 0) - 1) setIdx(idx + 1);
      }
      if (e.key === "ArrowRight" && !practice) setIdx((i) => Math.min(i + 1, (attempt?.questions.length ?? 1) - 1));
      if (e.key === "ArrowLeft" && !practice) setIdx((i) => Math.max(i - 1, 0));
    };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  });

  if (error) return <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center"><p className="font-semibold">{error}</p><Link href="/app/practice" className={buttonClass()}>Back to practice</Link></div>;
  if (!attempt || !q) return <div className="mx-auto max-w-3xl space-y-4 p-6"><Skeleton className="h-3" /><Skeleton className="h-40" /><Skeleton className="h-14" /><Skeleton className="h-14" /><Skeleton className="h-14" /></div>;
  if (submitted) return <Results attempt={attempt} returnTo={search.get("return")} onReview={(i) => { setIdx(i); }} />;

  const outOfHearts = attempt.hearts_enabled && attempt.hearts_remaining === 0;
  const isLast = idx === attempt.questions.length - 1;

  return (
    <div className="flex min-h-dvh flex-col">
      {/* header */}
      <header className="sticky top-0 z-20 border-b border-line bg-canvas/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-3xl items-center gap-3 px-4">
          <button onClick={() => setConfirmExit(true)} className="rounded-xl p-2 text-muted hover:bg-white hover:text-ink" aria-label="Exit quiz"><X className="h-6 w-6" /></button>
          <div className="flex-1">
            <Progress value={((practice ? answeredCount : idx + 1) / attempt.total_questions) * 100} className="h-3" animateIn={false} />
          </div>
          {attempt.hearts_enabled && (
            <div className="flex items-center gap-0.5" aria-label={`${attempt.hearts_remaining} hearts left`}>
              {[0, 1, 2].map((h) => (
                <motion.span key={h} animate={h >= attempt.hearts_remaining ? { scale: [1, 1.4, 0.9], opacity: 0.25 } : { scale: 1, opacity: 1 }}>
                  <Heart className="h-5 w-5 fill-red-500 text-red-500" />
                </motion.span>
              ))}
            </div>
          )}
          {attempt.deadline && <Countdown deadline={attempt.deadline} onExpire={submit} />}
          {!practice && (
            <button onClick={() => setPalette(true)} className="rounded-xl p-2 text-muted hover:bg-white hover:text-ink" aria-label="Question overview"><Grid3x3 className="h-6 w-6" /></button>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 pb-40 pt-6">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-bold text-muted">Question {idx + 1} <span className="font-medium">of {attempt.total_questions}</span></p>
          <div className="flex items-center gap-2">
            {q.topic && <Badge tone="gray" className="hidden sm:inline-flex">{q.topic}</Badge>}
            <Badge tone={q.difficulty === "Hard" ? "red" : q.difficulty === "Easy" ? "green" : "amber"}>{q.difficulty}</Badge>
            <button onClick={toggleFlag} className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ring-1 transition", q.flagged ? "bg-amber-400 text-ink ring-amber-400" : "text-muted ring-line hover:text-ink")} aria-pressed={q.flagged}>
              <Flag className="h-3.5 w-3.5" /> {q.flagged ? "Flagged" : "Flag"}
            </button>
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div key={q.id} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.2 }}>
            {q.passage && <Passage passage={q.passage} />}
            <Markdown className="mt-4 text-lg font-semibold leading-8 sm:text-xl">{q.text}</Markdown>
            {q.image_url && <img src={q.image_url} alt="Diagram for this question" className="mt-4 max-h-80 rounded-2xl border border-line bg-white object-contain" />}
            {q.table && Array.isArray(q.table) && (
              <div className="mt-4 overflow-x-auto"><table className="w-full border-collapse text-sm">{q.table.map((r: any[], i: number) => <tr key={i}>{r.map((c, j) => <td key={j} className="border border-line bg-white px-3 py-2">{c}</td>)}</tr>)}</table></div>
            )}
            {q.is_official_past_question && q.exam_year && <p className="mt-2 text-xs font-semibold text-muted">Past question · {q.exam_year}</p>}

            <div className="mt-6 grid gap-2.5" role="radiogroup" aria-label="Answer options">
              {q.options.map((o, i) => {
                const revealed = practice && q.answered;
                const selected = revealed ? q.selected_option === o.id : practice ? pending === o.id : q.selected_option === o.id;
                const state = revealed ? (o.id === q.correct_option ? "correct" : selected ? "wrong" : "dim") : selected ? "selected" : "idle";
                return (
                  <motion.button key={o.id} role="radio" aria-checked={selected} disabled={revealed || outOfHearts} onClick={() => choose(o.id)}
                    whileTap={!revealed ? { scale: 0.985 } : {}} animate={state === "wrong" ? { x: [0, -8, 8, -5, 5, 0] } : state === "correct" ? { scale: [1, 1.02, 1] } : {}}
                    className={cn("flex w-full items-center gap-3 rounded-2xl border-2 bg-white px-4 py-3.5 text-left text-[15px] font-semibold transition sm:py-4",
                      state === "idle" && "border-line border-b-4 hover:border-brand-300 hover:bg-brand-50/40",
                      state === "selected" && "border-brand-500 border-b-4 bg-brand-50 text-brand-900",
                      state === "correct" && "border-brand-500 bg-brand-50 text-brand-900",
                      state === "wrong" && "border-red-400 bg-red-50 text-red-800",
                      state === "dim" && "border-line opacity-55")}>
                    <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border-2 text-sm font-bold",
                      state === "selected" ? "border-brand-500 bg-brand-500 text-white" : state === "correct" ? "border-brand-500 bg-brand-500 text-white" : state === "wrong" ? "border-red-400 bg-red-400 text-white" : "border-line text-muted")}>
                      {state === "correct" ? <Check className="h-5 w-5" /> : state === "wrong" ? <X className="h-5 w-5" /> : o.label}
                    </span>
                    <Markdown className="min-w-0 flex-1 [&_p]:my-0">{o.text}</Markdown>
                  </motion.button>
                );
              })}
            </div>

            {practice && q.answered && <Feedback q={q} attemptId={attempt.id} subjectId={attempt.subject} topicId={attempt.topic} />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* sticky action bar */}
      <footer className={cn("safe-bottom fixed inset-x-0 bottom-0 z-20 border-t-2 transition-colors",
        practice && q.answered ? (q.is_correct ? "border-brand-200 bg-brand-50" : "border-red-200 bg-red-50") : "border-line bg-white")}>
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-4">
          {practice ? (
            <>
              <div className="min-w-0">
                {q.answered ? (
                  <p className={cn("flex items-center gap-2 text-lg font-extrabold", q.is_correct ? "text-brand-700" : "text-red-600")}>
                    {q.is_correct ? <CheckCircle2 className="h-7 w-7" /> : <XCircle className="h-7 w-7" />}{q.is_correct ? "Correct!" : "Not quite"}
                  </p>
                ) : outOfHearts ? <p className="font-bold text-red-600">Out of hearts!</p> : <p className="text-sm text-muted">{answeredCount}/{attempt.total_questions} answered</p>}
              </div>
              {outOfHearts || (q.answered && isLast) ? (
                <Button size="lg" onClick={submit} loading={submitting}>See results <ArrowRight className="h-5 w-5" /></Button>
              ) : q.answered ? (
                <Button size="lg" variant={q.is_correct ? "primary" : "danger"} onClick={() => setIdx(idx + 1)}>Continue <ArrowRight className="h-5 w-5" /></Button>
              ) : (
                <Button size="lg" onClick={check} disabled={pending === null} loading={saving} className="min-w-[140px]">Check</Button>
              )}
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={() => setIdx(idx - 1)} disabled={idx === 0}><ArrowLeft className="h-4 w-4" /> <span className="hidden sm:inline">Previous</span></Button>
              <p className="text-sm font-semibold text-muted">{answeredCount}/{attempt.total_questions} answered</p>
              {isLast ? (
                <Button onClick={() => setConfirmSubmit(true)}>Submit</Button>
              ) : (
                <Button onClick={() => setIdx(idx + 1)}><span className="hidden sm:inline">Next</span> <ArrowRight className="h-4 w-4" /></Button>
              )}
            </>
          )}
        </div>
      </footer>

      {/* exam palette */}
      <Drawer open={palette} onClose={() => setPalette(false)} title="Question overview">
        <div className="p-5">
          <h2 className="text-lg font-bold">Questions</h2>
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded bg-brand-600" /> Answered</span>
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded bg-amber-400" /> Flagged</span>
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded border border-line bg-white" /> Not answered</span>
          </div>
          <div className="mt-5 grid grid-cols-6 gap-2">
            {attempt.questions.map((x, i) => (
              <button key={x.id} onClick={() => { setIdx(i); setPalette(false); }}
                className={cn("relative h-11 rounded-xl text-sm font-bold ring-1 transition",
                  x.flagged ? "bg-amber-400 text-ink ring-amber-400" : x.answered ? "bg-brand-600 text-white ring-brand-600" : "bg-white ring-line",
                  i === idx && "ring-2 ring-ink ring-offset-2")}>{i + 1}</button>
            ))}
          </div>
          <Button className="mt-6 w-full" size="lg" onClick={() => { setPalette(false); setConfirmSubmit(true); }}>Submit assessment</Button>
        </div>
      </Drawer>

      <ConfirmDialog open={confirmSubmit} onClose={() => setConfirmSubmit(false)} onConfirm={submit} loading={submitting} title="Submit your answers?" confirmLabel="Submit now"
        body={answeredCount < attempt.total_questions
          ? <>You have <b className="text-ink">{attempt.total_questions - answeredCount} unanswered question{attempt.total_questions - answeredCount === 1 ? "" : "s"}</b>{attempt.questions.some((x) => x.flagged) ? " and some flagged for review" : ""}. Unanswered questions are marked wrong.</>
          : "You've answered every question. Ready to see how you did?"} />
      <ConfirmDialog open={confirmExit} onClose={() => setConfirmExit(false)} onConfirm={() => router.push("/app/practice")} title="Leave this quiz?" confirmLabel="Leave" danger
        body="Your answers are saved. You can come back to this quiz from Practice → Recent results until you submit." />
    </div>
  );
}

function Passage({ passage }: { passage: { title: string; body: string } }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="mt-4 rounded-2xl border border-line bg-white">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-bold" aria-expanded={open}>
        <span className="flex items-center gap-2"><BookOpenText className="h-4 w-4 text-brand-600" /> {passage.title || "Read the passage"}</span>
        <ChevronDown className={cn("h-4 w-4 transition", open && "rotate-180")} />
      </button>
      {open && <div className="max-h-72 overflow-y-auto border-t border-line px-4 py-3"><Markdown>{passage.body}</Markdown></div>}
    </div>
  );
}

function Feedback({ q, attemptId, subjectId, topicId }: { q: QuizQuestion; attemptId: number; subjectId: number | null; topicId: number | null }) {
  const correct = q.options.find((o) => o.id === q.correct_option);
  const mine = q.options.find((o) => o.id === q.selected_option);
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-5 overflow-hidden rounded-2xl border border-line bg-white">
      <div className="grid gap-px bg-line sm:grid-cols-2">
        <div className="bg-white p-4"><p className="text-xs font-bold uppercase text-muted">Your answer</p><div className={cn("mt-1 flex gap-2 font-semibold", q.is_correct ? "text-brand-700" : "text-red-600")}>{mine?.label}. <Markdown className="[&_p]:my-0">{mine?.text ?? "—"}</Markdown></div></div>
        <div className="bg-white p-4"><p className="text-xs font-bold uppercase text-muted">Correct answer</p><div className="mt-1 flex gap-2 font-semibold text-brand-700">{correct?.label}. <Markdown className="[&_p]:my-0">{correct?.text ?? "—"}</Markdown></div></div>
      </div>
      <div className="border-t border-line p-4">
        <p className="font-bold">{q.is_correct ? "Why it's right" : "Here's how to get it"}</p>
        {q.explanation && <Markdown className="mt-1">{q.explanation}</Markdown>}
        {q.solution_steps?.length ? (
          <ol className="mt-3 space-y-2">
            {q.solution_steps.map((s, i) => (
              <li key={i} className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">{i + 1}</span><Markdown className="[&_p]:my-0">{s}</Markdown></li>
            ))}
          </ol>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href={`/app/tutor?question=${q.id}&prompt=${encodeURIComponent(q.is_correct ? "Can you explain the concept behind this question?" : "Why is my answer incorrect? Explain step by step.")}`} className={buttonClass("secondary", "sm")}><Bot className="h-4 w-4" /> Ask AI Tutor</Link>
          {subjectId && <Link href={`/app/practice?kind=topic&subject=${subjectId}${topicId ? `&topic=${topicId}` : ""}`} className={buttonClass("soft", "sm")}><Swords className="h-4 w-4" /> Practise similar questions</Link>}
        </div>
      </div>
    </motion.div>
  );
}

function Countdown({ deadline, onExpire }: { deadline: string; onExpire: () => void }) {
  const end = useMemo(() => new Date(deadline).getTime(), [deadline]);
  const [left, setLeft] = useState(() => Math.max(0, Math.round((end - Date.now()) / 1000)));
  const fired = useRef(false);
  useEffect(() => {
    const t = setInterval(() => {
      const l = Math.max(0, Math.round((end - Date.now()) / 1000));
      setLeft(l);
      if (l === 0 && !fired.current) { fired.current = true; onExpire(); }
    }, 1000);
    return () => clearInterval(t);
  }, [end, onExpire]);
  const low = left < 300;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-bold tabular-nums", low ? "bg-red-50 text-red-600" : "bg-white text-ink ring-1 ring-line")} aria-live={low ? "polite" : "off"}>
      <Timer className="h-4 w-4" />{Math.floor(left / 3600) ? `${Math.floor(left / 3600)}:` : ""}{String(Math.floor((left % 3600) / 60)).padStart(2, "0")}:{String(left % 60).padStart(2, "0")}
    </span>
  );
}

/* ------------------------------------------------------------------ results */
function Results({ attempt, returnTo, onReview }: { attempt: Attempt; returnTo: string | null; onReview: (i: number) => void }) {
  const score = Math.round(Number(attempt.score_percent ?? 0));
  const rs = attempt.result_summary ?? {};
  const [review, setReview] = useState(false);
  const headline = score >= 85 ? "Outstanding!" : score >= 70 ? "Great work!" : score >= 50 ? "Good effort!" : "Every mistake is a lesson.";
  const color = score >= 70 ? "#16A34A" : score >= 50 ? "#F59E0B" : "#EF4444";

  return (
    <div className="mx-auto max-w-3xl px-4 pb-16 pt-8">
      <div className="flex items-center justify-between">
        <Link href="/app/practice" className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" /> Practice</Link>
        <Badge tone="gray">{attempt.kind_label}{attempt.subject_name ? ` · ${attempt.subject_name}` : ""}</Badge>
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-6 text-center">
        <div className="mx-auto w-fit"><Ring value={score} size={180} stroke={14} color={color}><div><CountUp value={score} className="text-5xl font-extrabold" /><span className="text-2xl font-extrabold">%</span><p className="text-xs font-semibold text-muted">score</p></div></Ring></div>
        <h1 className="mt-6 text-3xl font-extrabold">{headline}</h1>
        <p className="mt-1 text-muted">{score >= 70 ? "You're on track. Keep this up and you'll be exam-ready." : "Review the explanations below — that's where the real progress happens."}</p>
      </motion.div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          { l: "Correct", v: attempt.correct_count, i: CheckCircle2, c: "text-brand-600" },
          { l: "Incorrect", v: rs.incorrect ?? attempt.total_questions - attempt.correct_count, i: XCircle, c: "text-red-500" },
          { l: "Accuracy", v: `${rs.answered ? Math.round((attempt.correct_count / rs.answered) * 100) : 0}%`, i: Target, c: "text-sky-600" },
          { l: "Time", v: fmtDuration(attempt.time_spent_seconds), i: Clock, c: "text-slate-600" },
          { l: "XP earned", v: `+${attempt.xp_earned}`, i: null, c: "text-brand-700" },
        ].map((s, i) => (
          <motion.div key={s.l} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.07 }} className={cn("card p-4", i === 4 && "col-span-2 sm:col-span-1")}>
            <div className={cn("flex items-center gap-1.5 text-xs font-bold uppercase", s.c)}>{s.i ? <s.i className="h-4 w-4" /> : <XPGem size={16} />}{s.l}</div>
            <p className="mt-1 text-2xl font-extrabold">{s.v}</p>
          </motion.div>
        ))}
      </div>

      {rs.subjects?.length > 1 && (
        <section className="card mt-5 p-5">
          <h2 className="font-bold">By subject</h2>
          <div className="mt-3 space-y-3">{rs.subjects.map((s: any) => (
            <div key={s.subject}><div className="flex justify-between text-sm"><span className="font-semibold">{s.subject}</span><span className="font-bold">{s.percent}%</span></div><Progress value={s.percent} className="mt-1.5 h-2" /></div>
          ))}</div>
        </section>
      )}

      {rs.weak_topics?.length > 0 && (
        <section className="card mt-5 p-5">
          <h2 className="font-bold">Topics that need improvement</h2>
          <div className="mt-3 space-y-3">{rs.weak_topics.map((t: any) => (
            <div key={t.topic} className="flex items-center gap-3">
              <div className="min-w-0 flex-1"><div className="flex justify-between text-sm"><span className="font-semibold">{t.topic}</span><span className="text-muted">{t.correct}/{t.total}</span></div><Progress value={t.percent} className="mt-1.5 h-2" barClassName="from-amber-500 to-amber-400" /></div>
            </div>
          ))}</div>
        </section>
      )}

      <section className="mt-5">
        <h2 className="font-bold">Recommended next</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {(rs.recommendations ?? []).map((r: any) => (
            <Link key={r.label} href={r.type === "tutor" ? "/app/tutor" : r.type === "topic_quiz" ? `/app/practice?kind=topic&subject=${attempt.subject ?? ""}&topic=${r.topic_id ?? ""}` : "/app/practice?kind=subject"}
              className="card flex items-center gap-3 p-4 transition hover:-translate-y-0.5 hover:shadow-lift">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">{r.type === "tutor" ? <Bot className="h-5 w-5" /> : <Swords className="h-5 w-5" />}</span>
              <span><span className="block font-bold">{r.label}</span><span className="block text-sm text-muted">{r.reason}</span></span>
            </Link>
          ))}
        </div>
      </section>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        {returnTo ? (
          <Link href={returnTo} className={buttonClass("primary", "lg", "flex-1")}>Continue setup <ArrowRight className="h-5 w-5" /></Link>
        ) : (
          <Link href="/app" className={buttonClass("primary", "lg", "flex-1")}>Back to dashboard</Link>
        )}
        <Button variant="secondary" size="lg" className="flex-1" onClick={() => setReview(!review)}><RotateCcw className="h-5 w-5" /> {review ? "Hide" : "Review"} answers</Button>
      </div>

      {review && (
        <section className="mt-6 space-y-4">
          {attempt.questions.map((q, i) => (
            <div key={q.id} className="card p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-muted">Question {i + 1}</p>
                {q.is_correct ? <Badge>Correct</Badge> : q.selected_option ? <Badge tone="red">Incorrect</Badge> : <Badge tone="gray">Skipped</Badge>}
              </div>
              <Markdown className="mt-2 font-semibold">{q.text}</Markdown>
              <div className="mt-3 space-y-1.5">
                {q.options.map((o) => (
                  <div key={o.id} className={cn("flex gap-2 rounded-xl px-3 py-2 text-sm", o.id === q.correct_option ? "bg-brand-50 font-semibold text-brand-800" : o.id === q.selected_option ? "bg-red-50 text-red-700" : "text-muted")}>
                    <span className="font-bold">{o.label}.</span><Markdown className="[&_p]:my-0">{o.text}</Markdown>
                    {o.id === q.correct_option && <Check className="ml-auto h-4 w-4 shrink-0" />}
                  </div>
                ))}
              </div>
              {q.explanation && <div className="mt-3 rounded-xl bg-canvas p-3 text-sm"><Markdown>{q.explanation}</Markdown></div>}
              <Link href={`/app/tutor?question=${q.id}&prompt=${encodeURIComponent("Explain this question step by step.")}`} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700" onClick={() => onReview(i)}><Bot className="h-4 w-4" /> Ask AI Tutor</Link>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
