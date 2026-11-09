"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useInView } from "framer-motion";
import {
  ArrowRight, BookOpenCheck, Bot, BrainCircuit, CalendarDays, Check, CheckCircle2, ChevronDown, Crown, Flag,
  GraduationCap, Lock, MessageSquareText, Route, Sparkles, Swords, Target, Trophy, Users, X, Zap,
} from "lucide-react";
import { buttonClass } from "@/components/ui/button";
import { Badge, Progress } from "@/components/ui/primitives";
import { BadgeMedal, CreditCoin, DynIcon, Flame, XPGem, fireConfetti } from "@/components/ui/fun";
import { Markdown } from "@/components/ui/markdown";
import { cn, naira } from "@/lib/utils";

function Reveal({ children, className, delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}

function SectionHead({ eyebrow, title, body, dark, center = true }: { eyebrow: string; title: React.ReactNode; body?: string; dark?: boolean; center?: boolean }) {
  return (
    <Reveal className={cn("mb-12 max-w-2xl", center && "mx-auto text-center")}>
      <p className={cn("eyebrow", dark && "text-brand-400")}>{eyebrow}</p>
      <h2 className={cn("mt-3 text-3xl font-extrabold leading-tight sm:text-[2.6rem]", dark && "text-white")}>{title}</h2>
      {body && <p className={cn("mt-4 text-lg", dark ? "text-white/65" : "text-muted")}>{body}</p>}
    </Reveal>
  );
}

/* ---------------------------------------------------------------- exams strip */
export const EXAMS = [
  { code: "JAMB", name: "UTME", color: "#16A34A" }, { code: "WAEC", name: "WASSCE", color: "#0EA5E9" },
  { code: "NECO", name: "SSCE", color: "#8B5CF6" }, { code: "GCE", name: "Private", color: "#F59E0B" },
  { code: "NABTEB", name: "Business & Technical", color: "#EF4444" }, { code: "Post-UTME", name: "Screening", color: "#14532D" },
];

export function ExamStrip() {
  return (
    <section id="exams" className="border-y border-line bg-white py-10">
      <div className="container">
        <p className="text-center text-sm font-semibold text-muted">One account. Every major Nigerian examination — each with its own date, subjects and roadmap.</p>
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {EXAMS.map((e, i) => (
            <Reveal key={e.code} delay={i * 0.05}>
              <div className="group flex items-center gap-3 rounded-2xl border border-line bg-canvas px-4 py-3 transition hover:-translate-y-0.5 hover:border-brand-300 hover:bg-white hover:shadow-card">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white" style={{ background: e.color }}>
                  <GraduationCap className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <p className="font-extrabold leading-tight">{e.code}</p>
                  <p className="truncate text-xs text-muted">{e.name}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- how it works */
const STEPS = [
  { icon: Target, title: "Pick your exams", body: "Choose JAMB, WAEC, NECO or more, your exam date and your subjects — the rules are checked for you." },
  { icon: BrainCircuit, title: "Take a diagnostic", body: "A short assessment finds exactly what you know and which topics need work." },
  { icon: Route, title: "Get your roadmap", body: "A day-by-day plan built around your weak topics, your free time and your exam date." },
  { icon: Trophy, title: "Learn, play and pass", body: "Bite-size lessons, instant-feedback quizzes, streaks, XP and an AI tutor on call." },
];

export function HowItWorks() {
  return (
    <section id="how" className="py-20 sm:py-28">
      <div className="container">
        <SectionHead eyebrow="How Kwado AI works" title={<>From “where do I start?” to <span className="text-brand-600">exam-ready</span></>}
          body="Four simple steps. Kwado figures out what you need, so every minute of study counts." />
        <div className="relative grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          <div className="absolute left-0 right-0 top-10 hidden h-0.5 bg-gradient-to-r from-brand-100 via-brand-300 to-brand-100 lg:block" />
          {STEPS.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.1}>
              <div className="relative h-full rounded-3xl border border-line bg-white p-6 shadow-card transition hover:-translate-y-1 hover:shadow-lift">
                <div className="flex items-center justify-between">
                  <span className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-glow"><s.icon className="h-6 w-6" /></span>
                  <span className="text-5xl font-extrabold text-slate-100">0{i + 1}</span>
                </div>
                <h3 className="mt-5 text-lg font-bold">{s.title}</h3>
                <p className="mt-2 text-[15px] text-muted">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- interactive quiz */
const DEMO = {
  q: "A bag costs ₦5,000 and is sold at a discount of 20%. What is the selling price?",
  options: ["₦1,000", "₦4,000", "₦4,800", "₦6,000"],
  answer: 1,
  explain: "Discount = 20% of ₦5,000 = ₦1,000. Selling price = ₦5,000 − ₦1,000 = **₦4,000**.",
};

export function InteractivePreview() {
  const [pick, setPick] = useState<number | null>(null);
  const [xp, setXp] = useState(0);
  const correct = pick === DEMO.answer;
  const choose = (i: number) => {
    if (pick !== null) return;
    setPick(i);
    if (i === DEMO.answer) { setXp(15); fireConfetti(); }
  };
  return (
    <section id="features" className="bg-white py-20 sm:py-28">
      <div className="container grid items-center gap-12 lg:grid-cols-2 [&>*]:min-w-0">
        <div>
          <SectionHead center={false} eyebrow="Learning that feels like play" title="Every mistake is a lesson."
            body="Answer a question and you instantly see if you were right, the correct answer, and a clear step-by-step explanation. Try one now — no sign-up needed." />
          <ul className="space-y-3">
            {["Instant feedback in practice mode", "Exam mode hides answers until you submit — just like the real thing",
              "Explanations written and verified by teachers", "Ask the AI tutor about any question in one tap"].map((t) => (
              <li key={t} className="flex items-start gap-3 text-[15px]"><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />{t}</li>
            ))}
          </ul>
        </div>
        <Reveal>
          <div className="rounded-3xl border border-line bg-canvas p-5 shadow-lift sm:p-7">
            <div className="flex items-center justify-between">
              <Badge>Mathematics · Percentages</Badge>
              <div className="flex items-center gap-1.5 text-sm font-bold"><XPGem size={18} />
                <AnimatePresence mode="popLayout"><motion.span key={xp} initial={{ y: -12, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>{xp} XP</motion.span></AnimatePresence>
              </div>
            </div>
            <p className="mt-4 text-lg font-bold">{DEMO.q}</p>
            <div className="mt-5 grid gap-2.5">
              {DEMO.options.map((o, i) => {
                const state = pick === null ? "idle" : i === DEMO.answer ? "correct" : i === pick ? "wrong" : "dim";
                return (
                  <motion.button key={o} onClick={() => choose(i)} whileTap={pick === null ? { scale: 0.98 } : {}}
                    animate={state === "wrong" ? { x: [0, -6, 6, -4, 4, 0] } : {}}
                    className={cn("flex items-center gap-3 rounded-2xl border-2 bg-white px-4 py-3.5 text-left font-semibold transition",
                      state === "idle" && "border-line hover:border-brand-400 hover:bg-brand-50",
                      state === "correct" && "border-brand-500 bg-brand-50 text-brand-900",
                      state === "wrong" && "border-red-400 bg-red-50 text-red-800",
                      state === "dim" && "border-line opacity-60")}>
                    <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-2 text-sm",
                      state === "correct" ? "border-brand-500 bg-brand-500 text-white" : state === "wrong" ? "border-red-400 bg-red-400 text-white" : "border-line")}>
                      {state === "correct" ? <Check className="h-4 w-4" /> : state === "wrong" ? <X className="h-4 w-4" /> : "ABCD"[i]}
                    </span>
                    {o}
                  </motion.button>
                );
              })}
            </div>
            <AnimatePresence>
              {pick !== null && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn("mt-4 rounded-2xl p-4", correct ? "bg-brand-600 text-white" : "bg-ink text-white")}>
                  <p className="font-bold">{correct ? "Brilliant! +15 XP" : "Not quite — here's how it works"}</p>
                  <Markdown className="mt-1 text-white/90 [&_strong]:text-white">{DEMO.explain}</Markdown>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button onClick={() => { setPick(null); setXp(0); }} className="rounded-xl bg-white/15 px-3 py-1.5 text-sm font-semibold hover:bg-white/25">Try again</button>
                    <Link href="/register" className="rounded-xl bg-white px-3 py-1.5 text-sm font-semibold text-ink">Practise 1,000s more →</Link>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- AI tutor */
const CHAT = [
  { me: true, text: "Why is my answer for x² − 9 = 0 wrong? I wrote x = 3." },
  { me: false, text: "Good start — x = 3 works! But a quadratic usually has **two** roots.\n\n1. Factorise the difference of two squares: $x^2 - 9 = (x-3)(x+3)$\n2. Set each bracket to zero: $x = 3$ **or** $x = -3$\n\nQuick check: what are the roots of $x^2 - 16 = 0$?" },
];

export function TutorShowcase() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const t1 = setTimeout(() => setShown(1), 300);
    const t2 = setTimeout(() => setShown(2), 1900);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [inView]);
  return (
    <section className="relative overflow-hidden bg-ink-deep py-20 text-white sm:py-28">
      <div className="absolute inset-0 grid-bg-dark" />
      <div className="absolute -right-40 top-10 h-96 w-96 rounded-full bg-brand-600/30 blur-[120px]" />
      <div className="container relative grid items-center gap-12 lg:grid-cols-2 [&>*]:min-w-0">
        <Reveal className="order-2 lg:order-1">
          <div ref={ref} className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur sm:p-6">
            <div className="flex items-center gap-3 border-b border-white/10 pb-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600"><Bot className="h-5 w-5" /></span>
              <div><p className="font-bold">Kwado Tutor</p><p className="text-xs text-white/50">JAMB · Mathematics · Quadratic equations</p></div>
              <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-1 text-xs"><CreditCoin size={14} /> 2 credits / answer</span>
            </div>
            <div className="min-h-[300px] space-y-4 py-5">
              {CHAT.slice(0, shown).map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={cn("flex", m.me && "justify-end")}>
                  <div className={cn("max-w-[88%] rounded-2xl px-4 py-3 text-[15px]", m.me ? "rounded-br-md bg-brand-600" : "rounded-bl-md bg-white text-ink")}>
                    {m.me ? m.text : <Markdown>{m.text}</Markdown>}
                  </div>
                </motion.div>
              ))}
              {shown === 1 && (
                <div className="flex gap-1.5 rounded-2xl bg-white/10 px-4 py-3 w-fit" aria-label="Tutor is typing">
                  {[0, 1, 2].map((i) => <motion.span key={i} className="h-2 w-2 rounded-full bg-white/70" animate={{ y: [0, -5, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }} />)}
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {["Explain quadratic equations simply", "Give me five JAMB-style questions on genetics", "Teach me this step by step"].map((s) => (
                <span key={s} className="rounded-full border border-white/15 px-3 py-1.5 text-xs text-white/75">{s}</span>
              ))}
            </div>
          </div>
        </Reveal>
        <div className="order-1 lg:order-2">
          <SectionHead dark center={false} eyebrow="AI tutor" title="A patient tutor who never gets tired of your questions."
            body="Ask anything, any time. Kwado's tutor explains step by step, uses your exam and subject as context, and grounds answers in your syllabus and your own notes." />
          <div className="grid gap-4 sm:grid-cols-2">
            {[{ i: MessageSquareText, t: "Step-by-step solutions", b: "Maths in proper notation, not walls of text." },
              { i: Sparkles, t: "Knows your context", b: "Your exam, subject, topic and the question you missed." },
              { i: BookOpenCheck, t: "Verified answers win", b: "Official answer keys are never overridden by AI." },
              { i: CreditCoin as any, t: "Transparent pricing", b: "See the credit cost before you send. Failed answers are refunded." }].map((f) => (
              <div key={f.t} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <f.i className="h-5 w-5 text-brand-400" />
                <p className="mt-2 font-bold">{f.t}</p>
                <p className="mt-1 text-sm text-white/60">{f.b}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- roadmap */
const ROAD = [
  { d: "Mon", t: "Quadratic equations — lesson", k: "Lesson", s: "done" },
  { d: "Tue", t: "Practice: Genetics (20 questions)", k: "Practice", s: "done" },
  { d: "Wed", t: "Concord & Lexis — revision", k: "Revision", s: "current" },
  { d: "Thu", t: "Practice: Current electricity", k: "Practice", s: "upcoming" },
  { d: "Sat", t: "Full JAMB mock examination", k: "Mock", s: "upcoming" },
];

export function RoadmapPreview() {
  return (
    <section className="py-20 sm:py-28">
      <div className="container grid items-center gap-12 lg:grid-cols-2 [&>*]:min-w-0">
        <div>
          <SectionHead center={false} eyebrow="Personalised study roadmap" title="Know exactly what to study today."
            body="Your roadmap is built from your diagnostic results, topic mastery, study time and exam date — and it adapts as you improve. Each exam gets its own plan." />
          <div className="grid grid-cols-3 gap-2 sm:gap-3">
            {[["Weak topics first", Target], ["Weekly revision", CalendarDays], ["Mock exams built in", Flag]].map(([t, I]: any) => (
              <div key={t} className="min-w-0 rounded-2xl border border-line bg-white p-3 text-center shadow-card sm:p-4"><I className="mx-auto h-5 w-5 text-brand-600" /><p className="mt-2 text-sm font-semibold">{t}</p></div>
            ))}
          </div>
        </div>
        <Reveal>
          <div className="rounded-3xl border border-line bg-white p-5 shadow-lift sm:p-7">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-muted">JAMB UTME roadmap</p><p className="text-xl font-extrabold">Week 6 of 12</p></div>
              <Badge tone="dark">47 days left</Badge>
            </div>
            <Progress value={52} className="mt-4" />
            <ol className="relative mt-6 space-y-3 before:absolute before:bottom-4 before:left-[19px] before:top-4 before:w-0.5 before:bg-line">
              {ROAD.map((r, i) => (
                <motion.li key={r.t} initial={{ opacity: 0, x: 20 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                  className={cn("relative flex items-center gap-4 rounded-2xl p-2 pr-3", r.s === "current" && "bg-brand-50 ring-1 ring-brand-200")}>
                  <span className={cn("relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                    r.s === "done" ? "bg-brand-600 text-white" : r.s === "current" ? "bg-white text-brand-700 ring-2 ring-brand-500" : "bg-slate-100 text-muted")}>
                    {r.s === "done" ? <Check className="h-4 w-4" /> : r.d}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className={cn("truncate font-semibold", r.s === "done" && "text-muted line-through")}>{r.t}</p>
                    <p className="text-xs text-muted">{r.k}</p>
                  </div>
                  {r.s === "current" && <span className="rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-bold text-white">Today</span>}
                </motion.li>
              ))}
            </ol>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- gamification */
export function Gamification() {
  const [unlocked, setUnlocked] = useState(false);
  return (
    <section className="bg-white py-20 sm:py-28">
      <div className="container">
        <SectionHead eyebrow="Gamified, not childish" title={<>Come back tomorrow. <span className="text-brand-600">And the day after.</span></>}
          body="XP, levels, streaks, badges, missions and leaderboards turn consistent study into a habit you'll actually enjoy." />
        <div className="grid gap-4 md:grid-cols-6">
          <Reveal className="md:col-span-2">
            <div className="h-full rounded-3xl bg-ink p-6 text-white">
              <div className="flex items-center gap-2"><Flame size={40} /><span className="text-5xl font-extrabold">12</span></div>
              <p className="mt-2 font-bold">Day streak</p>
              <p className="mt-1 text-sm text-white/60">Learn a little every day. Streak freezes protect you on busy days.</p>
              <div className="mt-5 flex justify-between">{"MTWTFSS".split("").map((d, i) => <span key={i} className={cn("flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold", i < 6 ? "bg-flame text-white" : "bg-white/10")}>{d}</span>)}</div>
            </div>
          </Reveal>
          <Reveal className="md:col-span-2" delay={0.05}>
            <div className="h-full rounded-3xl border border-line bg-canvas p-6">
              <div className="flex items-center gap-2"><XPGem size={30} /><span className="text-3xl font-extrabold">Level 7</span></div>
              <p className="mt-1 text-sm text-muted">2,640 / 2,800 XP</p>
              <Progress value={86} className="mt-3 h-3" />
              <div className="mt-5 space-y-2 text-sm">
                {[["Correct answer", "+2 XP"], ["Lesson completed", "+20 XP"], ["Perfect quiz", "+20 XP bonus"], ["Mission complete", "+10–100 XP"]].map(([a, b]) => (
                  <div key={a} className="flex justify-between"><span className="text-muted">{a}</span><span className="font-bold text-brand-700">{b}</span></div>
                ))}
              </div>
            </div>
          </Reveal>
          <Reveal className="md:col-span-2" delay={0.1}>
            <div className="h-full rounded-3xl border border-line bg-canvas p-6">
              <p className="font-bold">Daily missions</p>
              <div className="mt-4 space-y-4">
                {[["Complete one mathematics lesson", 1, 1, 15], ["Answer 15 questions", 11, 15, 20], ["Ask the AI tutor one question", 0, 1, 10]].map(([t, p, n, x]: any) => (
                  <div key={t}>
                    <div className="flex justify-between text-sm"><span className="font-semibold">{t}</span><span className="text-xs font-bold text-brand-700">+{x} XP</span></div>
                    <Progress value={(p / n) * 100} className="mt-1.5 h-2" />
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
          <Reveal className="md:col-span-4" delay={0.05}>
            <div className="h-full rounded-3xl border border-line bg-canvas p-6">
              <div className="flex items-center justify-between">
                <p className="font-bold">Badges worth earning</p>
                <button onClick={() => { setUnlocked(true); fireConfetti(); }} className="text-sm font-semibold text-brand-700 hover:underline">{unlocked ? "Unlocked!" : "Tap to unlock one"}</button>
              </div>
              <div className="mt-5 grid grid-cols-3 gap-4 sm:grid-cols-6">
                {[["First Steps", "footprints", "bronze", true], ["Seven-Day Streak", "flame", "silver", true], ["Quiz Champion", "trophy", "silver", true],
                  ["Maths Master", "sigma", "gold", unlocked], ["Consistency King", "crown", "gold", false], ["Exam Ready", "graduation-cap", "emerald", false]].map(([n, i, t, e]: any) => (
                  <motion.div key={n} className="flex flex-col items-center text-center" animate={n === "Maths Master" && unlocked ? { scale: [1, 1.25, 1], rotate: [0, -8, 8, 0] } : {}}>
                    <BadgeMedal icon={i} tier={t} earned={e} size={60} />
                    <p className="mt-2 text-xs font-semibold leading-tight">{n}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          </Reveal>
          <Reveal className="md:col-span-2" delay={0.1}>
            <div className="h-full rounded-3xl border border-line bg-canvas p-6">
              <div className="flex items-center justify-between"><p className="font-bold">Weekly league</p><Crown className="h-5 w-5 text-gold" /></div>
              <ol className="mt-4 space-y-2">
                {[["Tobi A.", 1840], ["You", 1710], ["Learner #04821", 1655], ["Zainab M.", 1490]].map(([n, x]: any, i) => (
                  <li key={n} className={cn("flex items-center gap-3 rounded-xl px-3 py-2 text-sm", n === "You" ? "bg-brand-600 text-white" : "bg-white")}>
                    <span className="w-4 font-bold">{i + 1}</span><span className="flex-1 font-semibold">{n}</span><span className="font-bold">{x} XP</span>
                  </li>
                ))}
              </ol>
              <p className="mt-3 text-xs text-muted">Privacy first: show your name, appear anonymous, or hide entirely.</p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- subjects */
const SUBJECTS = [["English Language", "languages"], ["Mathematics", "sigma"], ["Physics", "atom"], ["Chemistry", "flask-conical"], ["Biology", "leaf"],
  ["Economics", "trending-up"], ["Government", "landmark"], ["Literature in English", "book-open"], ["Geography", "globe"], ["Commerce", "store"],
  ["Agricultural Science", "sprout"], ["Civic Education", "users"], ["Further Mathematics", "pi"], ["Financial Accounting", "calculator"],
  ["Christian Religious Studies", "church"], ["Islamic Studies", "moon-star"]];

export function SubjectCoverage() {
  return (
    <section className="py-20 sm:py-28">
      <div className="container">
        <SectionHead eyebrow="Subject coverage" title="Every core subject. Every examination rule." body="Science, arts and commercial subjects, with each exam's compulsory subjects and subject limits built in." />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {SUBJECTS.map(([n, i], idx) => (
            <Reveal key={n} delay={(idx % 4) * 0.04}>
              <div className="group flex items-center gap-3 rounded-2xl border border-line bg-white p-3.5 transition hover:border-brand-300 hover:shadow-card">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 transition group-hover:bg-brand-600 group-hover:text-white"><DynIcon name={i} className="h-5 w-5" /></span>
                <span className="text-sm font-semibold leading-tight">{n}</span>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- pricing */
const PACKAGES = [
  { name: "Starter", credits: 100, price: 1000 }, { name: "Basic", credits: 250, price: 2500 },
  { name: "Standard", credits: 500, price: 5000, featured: true }, { name: "Advanced", credits: 1000, price: 10000 },
  { name: "Premium", credits: 2500, price: 25000 },
];
const COSTS = [["Daily practice quiz (10 questions)", 5], ["Topic quiz (20 questions)", 10], ["Subject assessment (40 questions)", 15],
  ["Full mock examination", 25], ["Diagnostic assessment", 20], ["AI tutor response", 2], ["AI-generated practice set", 5],
  ["AI topic explanation", 3], ["AI roadmap generation", 15], ["Uploaded document analysis", 10]];

export function Pricing() {
  return (
    <section id="pricing" className="bg-white py-20 sm:py-28">
      <div className="container">
        <SectionHead eyebrow="Simple credit pricing" title="Pay only for what you use." body="No subscriptions. 1 credit = ₦10. Every new student gets 100 free credits — and you always see the cost before you start." />
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-none max-lg:-mx-4 max-lg:snap-x max-lg:px-4 lg:grid lg:grid-cols-5 lg:overflow-visible">
          {PACKAGES.map((p, i) => (
            <Reveal key={p.name} delay={i * 0.05} className="w-[230px] shrink-0 snap-center lg:w-auto">
              <div className={cn("relative flex h-full flex-col rounded-3xl border p-6 transition hover:-translate-y-1",
                p.featured ? "border-brand-600 bg-ink text-white shadow-glow" : "border-line bg-canvas hover:shadow-lift")}>
                {p.featured && <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-600 px-3 py-1 text-xs font-bold text-white">Most popular</span>}
                <p className={cn("font-bold", p.featured ? "text-brand-400" : "text-brand-700")}>{p.name}</p>
                <div className="mt-3 flex items-center gap-2"><CreditCoin size={26} /><span className="text-4xl font-extrabold">{p.credits.toLocaleString()}</span></div>
                <p className={cn("text-sm", p.featured ? "text-white/60" : "text-muted")}>credits</p>
                <p className="mt-5 text-2xl font-extrabold">{naira(p.price)}</p>
                <p className={cn("text-xs", p.featured ? "text-white/60" : "text-muted")}>≈ {Math.floor(p.credits / 5)} daily quizzes</p>
                <Link href="/register" className={cn("mt-6", buttonClass(p.featured ? "primary" : "secondary", "md", "w-full"))}>Choose {p.name}</Link>
              </div>
            </Reveal>
          ))}
        </div>
        <Reveal className="mt-10">
          <div className="rounded-3xl border border-line bg-canvas p-6 sm:p-8">
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
              <div><p className="text-lg font-bold">What things cost</p><p className="text-sm text-muted">Prices are shown before every paid activity. Failed AI responses are refunded automatically.</p></div>
              <p className="flex items-center gap-1.5 text-sm font-semibold text-brand-700"><Users className="h-4 w-4" /> Earn 20% back in credits on friends&apos; purchases</p>
            </div>
            <div className="mt-6 grid gap-x-10 sm:grid-cols-2">
              {COSTS.map(([a, c]) => (
                <div key={a as string} className="flex items-center justify-between border-b border-dashed border-line py-3 text-[15px]">
                  <span>{a}</span><span className="flex items-center gap-1 font-bold"><CreditCoin size={16} />{c}</span>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- testimonials */
const STORIES = [
  { n: "Chiamaka", r: "SS3 · Enugu", q: "The streaks got me studying every single day. My maths finally clicked when the tutor broke quadratics into steps." },
  { n: "Ibrahim", r: "UTME candidate · Kano", q: "I didn't know Physics was my weakest subject until the diagnostic. The roadmap told me exactly what to fix." },
  { n: "Toluwani", r: "WAEC candidate · Lagos", q: "Exam mode feels like the real thing. Seeing explanations after each mock helped me stop repeating mistakes." },
];

export function Testimonials() {
  return (
    <section className="py-20 sm:py-28">
      <div className="container">
        <SectionHead eyebrow="Student stories" title="Built for how Nigerian students really study." />
        <p className="-mt-8 mb-10 text-center text-xs font-semibold uppercase tracking-wider text-muted">Sample stories for illustration — real student testimonials coming soon</p>
        <div className="grid gap-5 md:grid-cols-3">
          {STORIES.map((s, i) => (
            <Reveal key={s.n} delay={i * 0.08}>
              <figure className="h-full rounded-3xl border border-line bg-white p-6 shadow-card">
                <div className="flex gap-0.5 text-gold">{Array.from({ length: 5 }).map((_, j) => <svg key={j} viewBox="0 0 20 20" className="h-4 w-4 fill-current"><path d="m10 1.5 2.6 5.6 6 .7-4.5 4.1 1.2 6L10 15l-5.3 2.9 1.2-6L1.4 7.8l6-.7z" /></svg>)}</div>
                <blockquote className="mt-4 text-[15px] leading-relaxed">“{s.q}”</blockquote>
                <figcaption className="mt-5 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-800">{s.n[0]}</span>
                  <div><p className="font-bold">{s.n}</p><p className="text-xs text-muted">{s.r} · sample</p></div>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- FAQ */
const FAQ = [
  ["Is Kwado AI free?", "Creating an account is free and you get 100 free credits — enough for a diagnostic, several quizzes and plenty of AI tutor questions. After that you top up with credits from ₦1,000; there's no subscription."],
  ["Which examinations are supported?", "JAMB UTME, WAEC WASSCE, NECO SSCE, GCE, NABTEB and Post-UTME screening. You can prepare for several at once, each with its own date, subjects and roadmap."],
  ["Are the questions official past questions?", "Questions are clearly labelled. Practice questions are original Kwado content written to examination standard, and every answer is verified by a person before it's published. AI never marks official questions."],
  ["How do I log in without a password?", "Enter your email and we send a 6-digit code that expires in 5 minutes. No passwords to forget or leak."],
  ["What happens if the AI tutor fails to answer?", "You're never charged for an incomplete AI response — credits are refunded automatically."],
  ["How do referrals work?", "Share your link. Whenever a friend you referred buys credits, you get 20% of the credits they purchased — for example 100 credits when they buy 500. Referral credits can't be withdrawn as cash."],
  ["Is my data safe?", "Your documents are private by default, payments are verified directly with Paystack, and we follow the Nigeria Data Protection Act. You control how you appear on leaderboards."],
];

export function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="bg-white py-20 sm:py-28">
      <div className="container max-w-3xl">
        <SectionHead eyebrow="FAQ" title="Questions, answered." />
        <div className="divide-y divide-line rounded-3xl border border-line bg-canvas">
          {FAQ.map(([q, a], i) => (
            <div key={q}>
              <button className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left font-bold sm:px-6" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                {q}<ChevronDown className={cn("h-5 w-5 shrink-0 text-muted transition", open === i && "rotate-180 text-brand-600")} />
              </button>
              <AnimatePresence initial={false}>
                {open === i && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                    <p className="px-5 pb-5 text-[15px] text-muted sm:px-6">{a}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- CTA */
export function FinalCta() {
  return (
    <section className="px-4 py-20 sm:py-24">
      <Reveal>
        <div className="relative mx-auto max-w-6xl overflow-hidden rounded-[2rem] bg-brand-700 px-6 py-16 text-center text-white sm:px-12">
          <div className="absolute inset-0 grid-bg-dark opacity-60" />
          <div className="absolute -left-20 -top-20 h-72 w-72 rounded-full bg-brand-400/40 blur-3xl" />
          <div className="absolute -bottom-24 -right-10 h-72 w-72 rounded-full bg-ink/40 blur-3xl" />
          <div className="relative">
            <div className="mx-auto mb-6 flex w-fit items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm font-semibold"><Zap className="h-4 w-4" /> Learn. Play. Practise. Pass.</div>
            <h2 className="mx-auto max-w-3xl text-3xl font-extrabold leading-tight sm:text-5xl">Every lesson brings you closer to success. Start yours today.</h2>
            <p className="mx-auto mt-4 max-w-xl text-lg text-white/80">Join free in under a minute and get 100 credits to try everything.</p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link href="/register" className={buttonClass("dark", "lg")}>Start Learning Free <ArrowRight className="h-5 w-5" /></Link>
              <Link href="/login" className={buttonClass("secondary", "lg", "border-0")}>I already have an account</Link>
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

export function Footer() {
  const cols = [
    ["Product", [["How it works", "#how"], ["Features", "#features"], ["Pricing", "#pricing"], ["FAQ", "#faq"]]],
    ["Examinations", [["JAMB UTME", "#exams"], ["WAEC WASSCE", "#exams"], ["NECO SSCE", "#exams"], ["GCE & NABTEB", "#exams"]]],
    ["Account", [["Create account", "/register"], ["Login", "/login"], ["Dashboard", "/app"], ["Refer a friend", "/app/referrals"]]],
    ["Company", [["Privacy policy", "/legal/privacy"], ["Terms of use", "/legal/terms"], ["Contact", "mailto:hello@kwado.ai"]]],
  ] as const;
  return (
    <footer className="bg-ink-deep pt-16 text-white">
      <div className="container grid gap-10 pb-12 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
        <div>
          <div className="flex items-center gap-2.5"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 font-extrabold">K</span><span className="text-lg font-extrabold">Kwado <span className="text-brand-400">AI</span></span></div>
          <p className="mt-4 max-w-xs text-sm text-white/60">Learn. Play. Practise. Pass. Every mistake is a lesson. Every lesson brings you closer to success.</p>
          <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1.5 text-xs text-white/60"><Lock className="h-3.5 w-3.5" /> Payments secured by Paystack</p>
        </div>
        {cols.map(([h, ls]) => (
          <div key={h}>
            <p className="text-sm font-bold">{h}</p>
            <ul className="mt-4 space-y-2.5">
              {ls.map(([l, href]) => <li key={l}><a href={href} className="text-sm text-white/60 transition hover:text-white">{l}</a></li>)}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10">
        <div className="container flex flex-col justify-between gap-2 py-6 text-xs text-white/50 sm:flex-row">
          <p>© {new Date().getFullYear()} Kwado AI. Made in Nigeria for Nigerian students.</p>
          <p>Kwado AI is independent and not affiliated with JAMB, WAEC, NECO or NABTEB.</p>
        </div>
      </div>
    </footer>
  );
}

