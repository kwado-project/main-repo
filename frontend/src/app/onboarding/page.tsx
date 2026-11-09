"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, BrainCircuit, CalendarDays, Check, Clock, GraduationCap, Lock, Map, Rocket, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Input, Progress, Skeleton } from "@/components/ui/primitives";
import { CreditCoin, DynIcon, fireConfetti } from "@/components/ui/fun";
import { Logo } from "@/components/ui/logo";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth";
import type { Examination, Pricing, StudentExam } from "@/lib/types";
import { cn, uid } from "@/lib/utils";

const STEPS = ["Welcome", "Examination", "Exam date", "Subjects", "Study time", "Diagnostic", "Roadmap"];
const STEP_FROM_SERVER: Record<string, number> = { date: 2, subjects: 3, study_time: 4, diagnostic: 5, roadmap: 6 };

export default function OnboardingPage() {
  return <Suspense><Onboarding /></Suspense>;
}

function Onboarding() {
  const me = useRequireAuth();
  const { reload } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const toast = useToast();
  const adding = params.get("add") === "1";
  const { data: exams } = useSWR<Examination[]>("/examinations");
  // Always read fresh profiles from the server so progress resumes correctly.
  const [myExams, setMyExams] = useState<StudentExam[] | null>(null);
  useEffect(() => { if (me) api<StudentExam[]>("/student-exams").then(setMyExams).catch(() => setMyExams([])); }, [me?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const { data: pricing } = useSWR<Pricing[]>("/wallet/pricing");
  const cost = (k: string) => pricing?.find((p) => p.key === k)?.credits ?? 0;

  const [step, setStep] = useState(adding ? 1 : 0);
  const [dir, setDir] = useState(1);
  const [se, setSe] = useState<StudentExam | null>(null);
  const [examId, setExamId] = useState<number | null>(null);
  const [date, setDate] = useState("");
  const [subjects, setSubjects] = useState<number[]>([]);
  const [minutes, setMinutes] = useState(45);
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [resumed, setResumed] = useState(false);

  // Resume an unfinished profile (progress is saved server-side after each step).
  useEffect(() => {
    if (!me || !myExams || resumed) return;
    setResumed(true);
    const target = params.get("se")
      ? myExams.find((x) => String(x.id) === params.get("se"))
      : !adding ? myExams.find((x) => x.onboarding_step !== "done") : undefined;
    if (target) {
      hydrate(target);
      setDir(1);
      setStep(STEP_FROM_SERVER[target.onboarding_step] ?? 1);
    } else if (!adding && myExams.some((x) => x.onboarding_step === "done")) {
      router.replace("/app");
    }
  }, [me, myExams]); // eslint-disable-line react-hooks/exhaustive-deps

  function hydrate(x: StudentExam) {
    setSe(x);
    setExamId(x.examination.id);
    setDate(x.exam_date ?? "");
    setSubjects(x.subjects.map((s) => s.id));
    setMinutes(x.daily_minutes);
    if (x.study_days?.length) setDays(x.study_days);
  }

  const exam = useMemo(() => exams?.find((e) => e.id === examId) ?? se?.examination ?? null, [exams, examId, se]);
  const compulsory = useMemo(() => exam?.subjects.filter((s) => s.is_compulsory).map((s) => s.subject.id) ?? [], [exam]);

  const go = (n: number) => { setDir(n > step ? 1 : -1); setErr(null); setStep(n); };

  async function save(patch: Record<string, unknown>, nextStepKey: string) {
    if (!se) return;
    const updated = await api<StudentExam>(`/student-exams/${se.id}`, { method: "PATCH", json: { ...patch, onboarding_step: nextStepKey } });
    setSe(updated);
  }

  async function next() {
    setBusy(true);
    setErr(null);
    try {
      if (step === 1) {
        if (!examId) throw new Error("Choose an examination to continue.");
        if (!se || se.examination.id !== examId) {
          const created = await api<StudentExam>("/student-exams", { method: "POST", json: { examination_id: examId } });
          hydrate(created);
          if (!created.subjects.length) {
            setSubjects(exams?.find((e) => e.id === examId)?.subjects.filter((s) => s.is_compulsory).map((s) => s.subject.id) ?? []);
          }
        }
      } else if (step === 2) {
        await save({ exam_date: date || null }, "subjects");
        if (!subjects.length) setSubjects(compulsory);
      } else if (step === 3) {
        await save({ subject_ids: subjects }, "study_time");
      } else if (step === 4) {
        await save({ daily_minutes: minutes, study_days: days }, "diagnostic");
      }
      go(step + 1);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function startDiagnostic() {
    if (!se) return;
    setBusy(true);
    try {
      await save({}, "roadmap");
      const a = await api<{ id: number }>("/assessments/attempts", {
        method: "POST", json: { kind: "diagnostic", student_exam: se.id, idempotency_key: `diag-${se.id}-${uid().slice(0, 12)}` },
      });
      router.push(`/app/quiz/${a.id}?return=${encodeURIComponent(`/onboarding?se=${se.id}`)}`);
    } catch (e) {
      setErr((e as ApiError).message);
      setBusy(false);
    }
  }

  async function generateRoadmap() {
    if (!se) return;
    setBusy(true);
    try {
      await api("/roadmaps/generate", { method: "POST", json: { student_exam: se.id } });
      await api(`/student-exams/${se.id}/activate`, { method: "POST" });
      await reload();
      fireConfetti({ big: true });
      toast({ tone: "success", title: "Your roadmap is ready!", body: "Today's tasks are waiting on your dashboard." });
      setTimeout(() => router.replace("/app/roadmap"), 900);
    } catch (e) {
      setErr((e as ApiError).message);
      setBusy(false);
    }
  }

  const canNext =
    (step === 1 && !!examId) ||
    step === 2 ||
    (step === 3 && !!exam && subjects.length >= exam.min_subjects && subjects.length <= exam.max_subjects && compulsory.every((c) => subjects.includes(c))) ||
    (step === 4 && days.length > 0);

  if (!me) return <div className="flex min-h-dvh items-center justify-center"><Skeleton className="h-64 w-80" /></div>;

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="sticky top-0 z-20 border-b border-line bg-white/85 backdrop-blur">
        <div className="container flex h-16 items-center gap-4">
          <Logo href={adding ? "/app" : "/"} />
          <div className="ml-auto flex w-40 items-center gap-3 sm:w-64">
            <Progress value={(step / (STEPS.length - 1)) * 100} className="h-2" animateIn={false} />
            <span className="shrink-0 text-xs font-semibold text-muted">{step + 1}/{STEPS.length}</span>
          </div>
        </div>
      </header>

      <main className="container flex max-w-3xl flex-1 flex-col py-8 sm:py-12">
        <AnimatePresence mode="wait" custom={dir}>
          <motion.div key={step} custom={dir}
            initial={{ opacity: 0, x: dir * 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: dir * -40 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }} className="flex-1">

            {step === 0 && (
              <div className="flex flex-col items-center pt-6 text-center">
                <motion.div initial={{ scale: 0, rotate: -20 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 200, damping: 12 }}
                  className="flex h-24 w-24 items-center justify-center rounded-3xl bg-brand-600 text-white shadow-glow"><Rocket className="h-11 w-11" /></motion.div>
                <h1 className="mt-8 text-3xl font-extrabold sm:text-4xl">Welcome to Kwado AI{me.full_name ? `, ${me.full_name.split(" ")[0]}` : ""}!</h1>
                <p className="mt-3 max-w-md text-lg text-muted">Let&apos;s set up your preparation in about two minutes. We&apos;ll build a study plan just for you.</p>
                <div className="mt-8 grid w-full max-w-md gap-3 text-left">
                  {[[GraduationCap, "Choose your exam and subjects"], [BrainCircuit, "Take a quick diagnostic"], [Map, "Get your personalised roadmap"]].map(([I, t]: any, i) => (
                    <motion.div key={t} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + i * 0.1 }} className="card flex items-center gap-4 p-4">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><I className="h-5 w-5" /></span>
                      <span className="font-semibold">{t}</span>
                    </motion.div>
                  ))}
                </div>
                <div className="mt-6 flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm text-white"><CreditCoin size={18} /> You have <b>{me.balance}</b> credits to get started</div>
              </div>
            )}

            {step === 1 && (
              <StepShell title="Which examination are you preparing for?" body="You can add more examinations later — each gets its own plan.">
                {!exams ? <div className="grid gap-3 sm:grid-cols-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28" />)}</div> : (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {exams.map((e) => {
                      const taken = (myExams ?? me.student_exams).some((x) => x.examination.id === e.id && x.id !== se?.id && x.onboarding_step === "done");
                      const sel = examId === e.id;
                      return (
                        <motion.button key={e.id} whileTap={{ scale: 0.98 }} disabled={taken} onClick={() => setExamId(e.id)}
                          className={cn("relative rounded-2xl border-2 bg-white p-5 text-left transition", sel ? "border-brand-600 shadow-glow" : "border-line hover:border-brand-300", taken && "opacity-50")}>
                          <div className="flex items-start gap-4">
                            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white" style={{ background: e.color }}><GraduationCap className="h-6 w-6" /></span>
                            <div className="min-w-0">
                              <p className="text-lg font-extrabold">{e.name}</p>
                              <p className="text-sm text-muted">{e.full_name}</p>
                              <p className="mt-2 text-xs font-semibold text-brand-700">{e.min_subjects === e.max_subjects ? `${e.min_subjects} subjects` : `${e.min_subjects}–${e.max_subjects} subjects`}</p>
                            </div>
                          </div>
                          {taken && <Badge tone="gray" className="absolute right-3 top-3">Added</Badge>}
                          {sel && <span className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-white"><Check className="h-4 w-4" /></span>}
                        </motion.button>
                      );
                    })}
                  </div>
                )}
              </StepShell>
            )}

            {step === 2 && (
              <StepShell title={`When is your ${exam?.name ?? "exam"}?`} body="We'll pace your roadmap to finish revision before the big day. Not sure yet? Pick an estimate — you can change it anytime.">
                <div className="card p-5 sm:p-6">
                  <label htmlFor="date" className="mb-2 flex items-center gap-2 font-semibold"><CalendarDays className="h-5 w-5 text-brand-600" /> Examination date</label>
                  <Input id="date" type="date" value={date} min={new Date(Date.now() + 86400000).toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)} className="text-lg" />
                  <div className="mt-4 flex flex-wrap gap-2">
                    {[["In 1 month", 30], ["In 3 months", 90], ["In 6 months", 182], ["In a year", 365]].map(([l, d]) => {
                      const v = new Date(Date.now() + (d as number) * 86400000).toISOString().slice(0, 10);
                      return <button key={l} onClick={() => setDate(v)} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold", date === v ? "border-brand-600 bg-brand-50 text-brand-800" : "border-line hover:border-brand-300")}>{l}</button>;
                    })}
                  </div>
                  {date && (
                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5 rounded-xl bg-brand-50 p-3 text-sm font-semibold text-brand-800">
                      {Math.max(0, Math.ceil((new Date(date).getTime() - Date.now()) / 86400000))} days to prepare — that&apos;s plenty of time with a good plan.
                    </motion.p>
                  )}
                </div>
              </StepShell>
            )}

            {step === 3 && exam && (
              <StepShell title="Choose your subjects" body={exam.rules_note || `Pick ${exam.min_subjects}–${exam.max_subjects} subjects.`}>
                <div className="mb-4 flex items-center justify-between rounded-2xl bg-white px-4 py-3 shadow-card ring-1 ring-line">
                  <span className="text-sm font-semibold">{subjects.length} selected</span>
                  <span className={cn("text-sm font-bold", subjects.length >= exam.min_subjects && subjects.length <= exam.max_subjects ? "text-brand-700" : "text-muted")}>
                    {exam.min_subjects === exam.max_subjects ? `Exactly ${exam.min_subjects}` : `${exam.min_subjects}–${exam.max_subjects}`} required
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                  {exam.subjects.map(({ subject: s, is_compulsory }) => {
                    const sel = subjects.includes(s.id);
                    const full = !sel && subjects.length >= exam.max_subjects;
                    return (
                      <motion.button key={s.id} whileTap={{ scale: 0.97 }} disabled={is_compulsory || full}
                        onClick={() => setSubjects((x) => (sel ? x.filter((i) => i !== s.id) : [...x, s.id]))}
                        className={cn("relative flex flex-col items-start gap-2 rounded-2xl border-2 bg-white p-3.5 text-left transition",
                          sel ? "border-brand-600 bg-brand-50/50" : "border-line hover:border-brand-300", full && "opacity-40")}>
                        <span className="flex h-9 w-9 items-center justify-center rounded-lg text-white" style={{ background: s.color }}><DynIcon name={s.icon} className="h-5 w-5" /></span>
                        <span className="text-sm font-bold leading-tight">{s.name}</span>
                        {is_compulsory && <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-700"><Lock className="h-3 w-3" /> Compulsory</span>}
                        {sel && <span className="absolute right-2.5 top-2.5 flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white"><Check className="h-3.5 w-3.5" /></span>}
                      </motion.button>
                    );
                  })}
                </div>
              </StepShell>
            )}

            {step === 4 && (
              <StepShell title="How much time can you study?" body="Be realistic — consistency beats cramming. Your roadmap fits around this.">
                <div className="card p-5 sm:p-6">
                  <p className="mb-3 flex items-center gap-2 font-semibold"><Clock className="h-5 w-5 text-brand-600" /> Each study day</p>
                  <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                    {[15, 30, 45, 60, 90, 120].map((m) => (
                      <button key={m} onClick={() => setMinutes(m)} className={cn("rounded-xl border-2 py-3 text-center font-bold transition", minutes === m ? "border-brand-600 bg-brand-600 text-white" : "border-line bg-white hover:border-brand-300")}>
                        {m < 60 ? `${m}m` : `${m / 60}h`}
                      </button>
                    ))}
                  </div>
                  <p className="mb-3 mt-7 font-semibold">Study days</p>
                  <div className="flex flex-wrap gap-2">
                    {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) => {
                      const on = days.includes(i);
                      return <button key={d} onClick={() => setDays((x) => on ? x.filter((y) => y !== i) : [...x, i].sort())} className={cn("h-11 w-14 rounded-xl border-2 text-sm font-bold", on ? "border-brand-600 bg-brand-50 text-brand-800" : "border-line bg-white text-muted")}>{d}</button>;
                    })}
                  </div>
                  <p className="mt-6 rounded-xl bg-canvas p-3 text-sm text-muted">That&apos;s about <b className="text-ink">{Math.round((minutes * days.length) / 60 * 10) / 10} hours</b> of focused study each week.</p>
                </div>
              </StepShell>
            )}

            {step === 5 && (
              <StepShell title="Let's find your starting point" body="A short diagnostic across your subjects shows exactly which topics to focus on. Answers are revealed when you finish.">
                <div className="card overflow-hidden">
                  <div className="bg-ink p-6 text-white">
                    <BrainCircuit className="h-8 w-8 text-brand-400" />
                    <p className="mt-3 text-xl font-bold">Diagnostic assessment</p>
                    <p className="mt-1 text-sm text-white/65">Up to 8 questions per subject · timed · no pressure — it&apos;s just a starting point.</p>
                  </div>
                  <div className="space-y-3 p-6">
                    <div className="flex items-center justify-between rounded-xl bg-canvas p-3">
                      <span className="text-sm font-semibold">Cost</span>
                      <span className="flex items-center gap-1.5 font-bold"><CreditCoin size={18} /> {cost("diagnostic")} credits</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl bg-canvas p-3">
                      <span className="text-sm font-semibold">Your balance</span>
                      <span className="font-bold">{me.balance} credits</span>
                    </div>
                    <Button size="lg" className="w-full" onClick={startDiagnostic} loading={busy}>Start diagnostic <ArrowRight className="h-5 w-5" /></Button>
                    <button onClick={async () => { await save({}, "roadmap"); go(6); }} className="w-full py-2 text-sm font-semibold text-muted hover:text-ink">Skip for now — I&apos;ll take it later</button>
                  </div>
                </div>
              </StepShell>
            )}

            {step === 6 && (
              <StepShell title="Generate your personalised roadmap" body="We combine your exam date, subjects, study time and diagnostic results into a day-by-day plan with weekly revision and mock exams.">
                <div className="card p-6">
                  <ul className="space-y-3">
                    {[`${exam?.name} on ${date ? new Date(date).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "a date to be confirmed"}`,
                      `${subjects.length} subjects`, `${minutes} minutes a day, ${days.length} days a week`, "Weak topics prioritised automatically"].map((t) => (
                      <li key={t} className="flex items-center gap-3"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-brand-700"><Check className="h-4 w-4" /></span><span className="font-medium">{t}</span></li>
                    ))}
                  </ul>
                  <div className="mt-6 flex items-center justify-between rounded-xl bg-canvas p-3">
                    <span className="flex items-center gap-2 text-sm font-semibold"><Sparkles className="h-4 w-4 text-brand-600" /> AI roadmap generation</span>
                    <span className="flex items-center gap-1.5 font-bold"><CreditCoin size={18} /> {cost("ai_roadmap")} credits</span>
                  </div>
                  <p className="mt-2 text-xs text-muted">Charged only if the AI coaching summary completes. Your plan is created either way.</p>
                  <Button size="lg" className="mt-5 w-full" onClick={generateRoadmap} loading={busy}>Build my roadmap <Sparkles className="h-5 w-5" /></Button>
                </div>
              </StepShell>
            )}
          </motion.div>
        </AnimatePresence>

        {err && <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{err}</p>}

        {step < 5 && (
          <div className="sticky bottom-0 -mx-4 mt-8 flex items-center justify-between gap-3 border-t border-line bg-canvas/95 px-4 py-4 backdrop-blur sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0">
            <Button variant="ghost" onClick={() => go(step - 1)} disabled={step === 0 || (adding && step === 1)}><ArrowLeft className="h-4 w-4" /> Back</Button>
            <Button size="lg" onClick={step === 0 ? () => go(1) : next} disabled={step > 0 && !canNext} loading={busy}>
              {step === 0 ? "Let's go" : "Continue"} <ArrowRight className="h-5 w-5" />
            </Button>
          </div>
        )}
        {step >= 5 && <div className="mt-6"><Button variant="ghost" onClick={() => go(step - 1)}><ArrowLeft className="h-4 w-4" /> Back</Button></div>}
      </main>
    </div>
  );
}

function StepShell({ title, body, children }: { title: string; body?: string; children: React.ReactNode }) {
  return (
    <div>
      <h1 className="text-2xl font-extrabold sm:text-3xl">{title}</h1>
      {body && <p className="mt-2 text-muted">{body}</p>}
      <div className="mt-7">{children}</div>
    </div>
  );
}
