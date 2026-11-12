"use client";
import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Step = { target?: string; title: string; body: string };

const STEPS: Step[] = [
  { title: "Welcome to Kwado AI! 🎉", body: "Here's a quick look around so you know where everything is. It takes about 30 seconds." },
  { target: "exam", title: "Your exam", body: "This is the exam you're preparing for, with a countdown to exam day. Tap it to switch between exams or add another one." },
  { target: "xp", title: "XP and streaks", body: "Earn XP for every lesson and quiz you finish. Study every day to keep your streak going." },
  { target: "credits", title: "Your credits", body: "Credits pay for things like the AI tutor and mock exams. Your free welcome credits are already here. Tap to top up." },
  { target: "learn", title: "Learn", body: "Short lessons for every topic in your subjects, one step at a time." },
  { target: "practice", title: "Practice", body: "Practise exam-style questions by subject and topic, and take timed mock exams." },
  { target: "tutor", title: "AI tutor", body: "Stuck on a question? Ask the AI tutor at any time and get a step-by-step explanation." },
  { target: "roadmap", title: "Your roadmap", body: "A study plan built around your exam date and your weak topics, so you always know what to do next." },
  { target: "referrals", title: "Refer and earn", body: "Invite friends with your link. They get free credits, and you earn credits every time they buy." },
  { title: "You're all set!", body: "Start with today's plan on your home page. You can take this tour again any time from the menu (Take the tour)." },
];

const PAD = 8;

/** The first element with this data-tour key that is actually on screen (desktop sidebar vs mobile bottom bar). */
function findTarget(key?: string): HTMLElement | null {
  if (!key) return null;
  for (const el of Array.from(document.querySelectorAll<HTMLElement>(`[data-tour="${key}"]`))) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden") return el;
  }
  return null;
}

export const TOUR_EVENT = "kwado:start-tour";
export const startTour = () => window.dispatchEvent(new Event(TOUR_EVENT));

export function ProductTour() {
  const { me, reload } = useAuth();
  const [open, setOpen] = useState(false);
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [vw, setVw] = useState(0);
  const [vh, setVh] = useState(0);

  // First visit after sign-up/login (once onboarding is done), or on demand from the menu.
  useEffect(() => {
    if (me && me.profile?.onboarding_completed && !me.profile?.tour_completed) {
      const t = setTimeout(() => { setI(0); setOpen(true); }, 700);
      return () => clearTimeout(t);
    }
  }, [me]);
  useEffect(() => {
    const on = () => { setI(0); setOpen(true); };
    window.addEventListener(TOUR_EVENT, on);
    return () => window.removeEventListener(TOUR_EVENT, on);
  }, []);

  const step = STEPS[i];
  const measure = useCallback(() => {
    setVw(window.innerWidth);
    setVh(window.innerHeight);
    const el = findTarget(step?.target);
    setRect(el ? el.getBoundingClientRect() : null);
  }, [step]);

  useLayoutEffect(() => {
    if (!open) return;
    const el = findTarget(step?.target);
    if (el) {
      const r = el.getBoundingClientRect();
      if (r.top < 80 || r.bottom > window.innerHeight - 80) el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
    measure();
    const t = setTimeout(measure, 350); // after smooth scroll
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => { clearTimeout(t); window.removeEventListener("resize", measure); window.removeEventListener("scroll", measure, true); };
  }, [open, i, step, measure]);

  const finish = useCallback(async () => {
    setOpen(false);
    if (me && !me.profile?.tour_completed) {
      try { await api("/me", { method: "PATCH", json: { profile: { tour_completed: true } } }); await reload(); } catch {}
    }
  }, [me, reload]);

  const next = useCallback(() => (i < STEPS.length - 1 ? setI(i + 1) : finish()), [i, finish]);
  const back = useCallback(() => setI((x) => Math.max(0, x - 1)), []);

  useEffect(() => {
    if (!open) return;
    const on = (e: KeyboardEvent) => {
      if (e.key === "Escape") finish();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") back();
    };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, [open, next, back, finish]);

  if (!open || !step) return null;

  // Card placement: below the target if there's room, otherwise above; centred when there's no target.
  const cardW = Math.min(360, vw - 32);
  let style: React.CSSProperties;
  if (rect) {
    const left = Math.min(Math.max(16, rect.left + rect.width / 2 - cardW / 2), vw - cardW - 16);
    const below = rect.bottom + PAD + 12;
    style = vh - rect.bottom > 240 ? { left, top: below, width: cardW } : { left, bottom: vh - rect.top + PAD + 12, width: cardW };
  } else {
    // Explicit coordinates: framer-motion owns `transform` on this element, so translate(-50%) can't be used.
    style = { left: Math.max(16, (vw - cardW) / 2), top: Math.max(16, vh / 2 - 130), width: cardW };
  }

  return (
    <div className="fixed inset-0 z-[100]" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      {/* dim layer; the spotlight is a transparent box with a huge shadow */}
      {rect ? (
        <motion.div className="pointer-events-none fixed rounded-2xl ring-2 ring-brand-400"
          initial={false}
          animate={{ left: rect.left - PAD, top: rect.top - PAD, width: rect.width + PAD * 2, height: rect.height + PAD * 2 }}
          transition={{ type: "spring", stiffness: 380, damping: 34 }}
          style={{ boxShadow: "0 0 0 9999px rgba(10, 20, 15, 0.62)" }} />
      ) : (
        <div className="fixed inset-0 bg-[rgba(10,20,15,0.62)]" />
      )}
      <div className="fixed inset-0" onClick={(e) => e.stopPropagation()} />

      <AnimatePresence mode="wait">
        <motion.div key={i} initial={{ opacity: 0, y: 8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }} className="fixed rounded-2xl bg-white p-5 shadow-lift ring-1 ring-line" style={style}>
          <button onClick={finish} className="absolute right-3 top-3 rounded-lg p-1.5 text-muted hover:bg-slate-100" aria-label="Close tour"><X className="h-4 w-4" /></button>
          {!step.target && <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><Sparkles className="h-5 w-5" /></span>}
          <h2 id="tour-title" className="pr-6 text-lg font-extrabold">{step.title}</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-muted">{step.body}</p>
          <div className="mt-4 flex items-center gap-2">
            <div className="flex flex-1 gap-1" aria-label={`Step ${i + 1} of ${STEPS.length}`}>
              {STEPS.map((_, k) => <span key={k} className={`h-1.5 rounded-full transition-all ${k === i ? "w-5 bg-brand-600" : "w-1.5 bg-slate-200"}`} />)}
            </div>
            {i === 0 ? (
              <button onClick={finish} className="rounded-xl px-3 py-2 text-sm font-semibold text-muted hover:bg-slate-50">Skip</button>
            ) : (
              <button onClick={back} className="rounded-xl p-2 text-muted hover:bg-slate-50" aria-label="Previous"><ArrowLeft className="h-4 w-4" /></button>
            )}
            <button onClick={next} autoFocus className="inline-flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white shadow-press hover:bg-brand-700">
              {i === 0 ? "Show me" : i === STEPS.length - 1 ? "Let's go" : "Next"} {i < STEPS.length - 1 && <ArrowRight className="h-4 w-4" />}
            </button>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
