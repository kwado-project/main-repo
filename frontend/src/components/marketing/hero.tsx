"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Bell, CalendarClock, Check, PlayCircle, Sparkles, Star, Target, Trophy } from "lucide-react";
import { buttonClass } from "@/components/ui/button";
import { CountUp, Progress, Ring } from "@/components/ui/primitives";
import { CreditCoin, Flame, XPGem } from "@/components/ui/fun";
import { cn } from "@/lib/utils";

import type { Variants } from "framer-motion";
const fadeUp: Variants = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const } } };

export function Hero() {
  return (
    <section id="home" className="relative overflow-hidden pt-28 sm:pt-32 lg:pt-36">
      <div className="absolute inset-0 -z-10 grid-bg [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_70%)]" />
      <div className="absolute -top-40 left-1/2 -z-10 h-[560px] w-[960px] -translate-x-1/2 rounded-full bg-brand-200/50 blur-[120px]" />
      <div className="container grid items-center gap-14 pb-16 lg:grid-cols-[1.02fr_1fr] lg:gap-10 lg:pb-24">
        <motion.div initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.08 } } }} className="text-center lg:text-left">
          <motion.div variants={fadeUp} className="mb-5 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/80 py-1 pl-1 pr-3.5 text-sm font-medium text-brand-800 shadow-card backdrop-blur">
            <span className="rounded-full bg-brand-600 px-2 py-0.5 text-xs font-bold text-white">New</span>
            JAMB · WAEC · NECO · GCE · NABTEB · Post-UTME
          </motion.div>
          <motion.h1 variants={fadeUp} className="text-[2.6rem] font-extrabold leading-[1.04] tracking-tight sm:text-6xl lg:text-[4.1rem]">
            Your Next Exam Success <span className="relative whitespace-nowrap text-brand-600">Starts Here.
              <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" fill="none" aria-hidden>
                <motion.path d="M2 9c60-6 160-8 296-3" stroke="#86EFAC" strokeWidth="5" strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.7, duration: 0.9 }} />
              </svg>
            </span>
          </motion.h1>
          <motion.p variants={fadeUp} className="mx-auto mt-6 max-w-xl text-lg text-muted sm:text-xl lg:mx-0">
            Prepare smarter, practise better, and achieve your academic goals with personalised AI-powered learning.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center lg:justify-start">
            <Link href="/register" className={buttonClass("primary", "lg", "group")}>
              Start Learning Free <ArrowRight className="h-5 w-5 transition group-hover:translate-x-0.5" />
            </Link>
            <a href="#how" className={buttonClass("secondary", "lg")}>
              <PlayCircle className="h-5 w-5 text-brand-600" /> Explore How It Works
            </a>
          </motion.div>
          <motion.div variants={fadeUp} className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-muted lg:justify-start">
            <span className="inline-flex items-center gap-2"><CreditCoin size={18} /> 100 free credits on sign-up</span>
            <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-brand-600" /> No password to remember</span>
            <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-brand-600" /> Works on any phone</span>
          </motion.div>
        </motion.div>
        <ProductPreview />
      </div>
    </section>
  );
}

/* ---------- animated product preview (demo data, clearly labelled) ---------- */

function ProductPreview() {
  const [xp, setXp] = useState(1240);
  const [answered, setAnswered] = useState<number | null>(null);
  const [fly, setFly] = useState(0);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    let i = 0;
    const id = setInterval(() => {
      i++;
      if (i % 3 === 1) setAnswered(2);
      if (i % 3 === 2) { setFly((f) => f + 1); setTimeout(() => setXp((x) => x + 15), 700); }
      if (i % 3 === 0) setAnswered(null);
    }, 1800);
    return () => clearInterval(id);
  }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 40, rotate: -1 }} animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ duration: 0.9, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
      className="relative mx-auto w-full max-w-[540px]" aria-label="Kwado AI product preview with sample data">
      {/* floating chips */}
      <motion.div className="absolute -left-4 top-24 z-20 hidden rounded-2xl bg-white p-3 shadow-lift ring-1 ring-line sm:block" animate={{ y: [0, -10, 0] }} transition={{ duration: 6, repeat: Infinity }}>
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-50"><Trophy className="h-5 w-5 text-gold" /></div>
          <div><p className="text-xs text-muted">Badge unlocked</p><p className="text-sm font-bold">Seven-Day Streak</p></div>
        </div>
      </motion.div>
      <motion.div className="absolute -right-3 bottom-28 z-20 hidden rounded-2xl bg-ink p-3 text-white shadow-lift sm:block" animate={{ y: [0, 10, 0] }} transition={{ duration: 7, repeat: Infinity }}>
        <div className="flex items-center gap-2.5">
          <Sparkles className="h-5 w-5 text-brand-400" />
          <p className="text-sm font-semibold">“Let&apos;s factorise it step by step…”</p>
        </div>
      </motion.div>

      <div className="relative rounded-[28px] bg-ink-deep p-2.5 shadow-[0_40px_80px_-30px_rgba(20,83,45,.55)] ring-1 ring-white/10">
        <div className="flex items-center gap-1.5 px-3 pb-2.5 pt-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-white/20" /><span className="h-2.5 w-2.5 rounded-full bg-white/20" /><span className="h-2.5 w-2.5 rounded-full bg-white/20" />
          <span className="ml-3 rounded-md bg-white/10 px-2 py-0.5 text-[10px] font-medium text-white/60">Preview · sample data</span>
        </div>
        <div className="overflow-hidden rounded-[20px] bg-canvas p-4 sm:p-5">
          {/* top bar */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted">Good morning,</p>
              <p className="text-lg font-extrabold">Amaka</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1.5 shadow-card ring-1 ring-line">
                <XPGem size={16} />
                <span className="text-sm font-bold tabular-nums"><CountUp value={xp} duration={0.6} /></span>
                <AnimatePresence>
                  {fly > 0 && (
                    <motion.span key={fly} className="absolute left-1 top-1" initial={{ x: -60, y: 200, opacity: 0, scale: 1.4 }} animate={{ x: 0, y: 0, opacity: [0, 1, 1, 0], scale: 1 }} transition={{ duration: 0.8, ease: "easeIn" }}>
                      <XPGem size={16} />
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
              <div className="flex items-center gap-1 rounded-full bg-white px-2.5 py-1.5 shadow-card ring-1 ring-line">
                <Flame size={18} /><span className="text-sm font-bold">12</span>
              </div>
              <div className="hidden h-8 w-8 items-center justify-center rounded-full bg-white shadow-card ring-1 ring-line sm:flex"><Bell className="h-4 w-4" /></div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-5 gap-3">
            {/* countdown */}
            <div className="col-span-3 rounded-2xl bg-ink p-4 text-white">
              <div className="flex items-center gap-1.5 text-xs text-white/60"><CalendarClock className="h-3.5 w-3.5" /> JAMB UTME</div>
              <div className="mt-1 flex items-end gap-1.5"><span className="text-3xl font-extrabold">47</span><span className="mb-1 text-sm text-white/70">days to go</span></div>
              <div className="mt-3"><Progress value={68} className="h-2 bg-white/10" /></div>
              <p className="mt-1.5 text-[11px] text-white/60">68% of roadmap complete</p>
            </div>
            {/* level ring */}
            <div className="col-span-2 flex flex-col items-center justify-center rounded-2xl bg-white p-3 shadow-card ring-1 ring-line">
              <Ring value={72} size={70} stroke={7}><span className="text-lg font-extrabold">L7</span></Ring>
              <p className="mt-1.5 text-[11px] font-semibold text-muted">160 XP to L8</p>
            </div>
          </div>

          {/* quiz card */}
          <div className="mt-3 rounded-2xl bg-white p-4 shadow-card ring-1 ring-line">
            <div className="flex items-center justify-between text-xs font-semibold text-muted">
              <span className="inline-flex items-center gap-1"><Target className="h-3.5 w-3.5 text-brand-600" /> Mathematics · Quadratics</span>
              <span>4 / 10</span>
            </div>
            <Progress value={40} className="mt-2 h-1.5" animateIn={false} />
            <p className="mt-3 text-[15px] font-bold">Solve x² − 5x + 6 = 0</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {["x = 1 or 6", "x = −2 or −3", "x = 2 or 3", "x = 5 or 6"].map((o, i) => (
                <div key={o} className={cn("rounded-xl border-2 px-3 py-2 text-sm font-semibold transition-colors duration-300",
                  answered === 2 && i === 2 ? "border-brand-500 bg-brand-50 text-brand-800" : "border-line bg-white")}>
                  <span className="mr-1.5 text-muted">{"ABCD"[i]}.</span>{o}
                </div>
              ))}
            </div>
            <AnimatePresence>
              {answered === 2 && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="mt-3 flex items-center gap-2 rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white">
                    <Check className="h-4 w-4" /> Correct! (x − 2)(x − 3) = 0 <span className="ml-auto">+15 XP</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* streak week + credits */}
          <div className="mt-3 grid grid-cols-5 gap-3">
            <div className="col-span-3 rounded-2xl bg-white p-3 shadow-card ring-1 ring-line">
              <p className="text-xs font-semibold text-muted">This week</p>
              <div className="mt-2 flex justify-between">
                {"MTWTFSS".split("").map((d, i) => (
                  <div key={i} className="flex flex-col items-center gap-1">
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.8 + i * 0.07, type: "spring" }}
                      className={cn("flex h-6 w-6 items-center justify-center rounded-full", i < 5 ? "bg-brand-600 text-white" : "bg-slate-100")}>
                      {i < 5 && <Check className="h-3.5 w-3.5" />}
                    </motion.div>
                    <span className="text-[10px] text-muted">{d}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="col-span-2 rounded-2xl bg-brand-50 p-3 ring-1 ring-brand-100">
              <p className="text-xs font-semibold text-brand-800">Credits</p>
              <div className="mt-1 flex items-center gap-1.5"><CreditCoin size={18} /><span className="text-xl font-extrabold">340</span></div>
              <p className="mt-0.5 flex items-center gap-1 text-[11px] text-brand-800"><Star className="h-3 w-3" /> 3 missions left</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
