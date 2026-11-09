"use client";
import { motion, useReducedMotion } from "framer-motion";
import {
  Atom, BookOpen, BookOpenCheck, Calculator, Church, Crown, Flame as FlameIcon, FlaskConical, Footprints, Globe, GraduationCap,
  Landmark, Languages, Leaf, ListChecks, Lock, MoonStar, Pi, Sigma, Sparkles, Sprout, Star, Store, Target, TrendingUp, Trophy,
  Users, Zap, type LucideIcon,
} from "lucide-react";

// Explicit map (instead of importing every icon) keeps the bundle small on mobile data.
const ICONS: Record<string, LucideIcon> = {
  atom: Atom, "book-open": BookOpen, "book-open-check": BookOpenCheck, calculator: Calculator, church: Church, crown: Crown,
  flame: FlameIcon, "flask-conical": FlaskConical, footprints: Footprints, globe: Globe, "graduation-cap": GraduationCap,
  landmark: Landmark, languages: Languages, leaf: Leaf, "list-checks": ListChecks, lock: Lock, "moon-star": MoonStar, pi: Pi,
  sigma: Sigma, sparkles: Sparkles, sprout: Sprout, star: Star, store: Store, target: Target, "trending-up": TrendingUp,
  trophy: Trophy, users: Users, zap: Zap,
};
import { cn } from "@/lib/utils";

export async function fireConfetti(opts: { big?: boolean } = {}) {
  if (typeof window === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const confetti = (await import("canvas-confetti")).default;
  const colors = ["#16A34A", "#22C55E", "#86EFAC", "#F5B400", "#FFFFFF", "#111827"];
  confetti({ particleCount: opts.big ? 160 : 90, spread: 80, origin: { y: 0.6 }, colors, disableForReducedMotion: true });
  if (opts.big) {
    setTimeout(() => confetti({ particleCount: 70, angle: 60, spread: 60, origin: { x: 0 }, colors }), 220);
    setTimeout(() => confetti({ particleCount: 70, angle: 120, spread: 60, origin: { x: 1 }, colors }), 380);
  }
}

export function DynIcon({ name, className }: { name: string; className?: string }) {
  const Icon = ICONS[name] ?? BookOpen;
  return <Icon className={className} />;
}

export function Flame({ active = true, size = 28, className }: { active?: boolean; size?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.svg viewBox="0 0 24 24" width={size} height={size} className={cn(className)} aria-hidden
      animate={active && !reduce ? { scale: [1, 1.08, 1], rotate: [-2, 2, -2] } : {}} transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}>
      <defs>
        <linearGradient id="flameG" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor={active ? "#EA580C" : "#94A3B8"} />
          <stop offset="1" stopColor={active ? "#FACC15" : "#CBD5E1"} />
        </linearGradient>
      </defs>
      <path fill="url(#flameG)" d="M12 2c.6 3.2-1.2 5-2.6 6.6C8 10.2 7 11.7 7 14a5 5 0 0 0 10 0c0-1.8-.7-3.2-1.6-4.3-.3 1.3-1 2.2-2 2.6.4-2.8-.2-6.3-1.4-10.3Z" />
      <path fill={active ? "#FEF3C7" : "#E2E8F0"} d="M12 13.2c.9 1 1.6 1.8 1.6 3a1.6 1.6 0 0 1-3.2 0c0-1 .7-1.9 1.6-3Z" />
    </motion.svg>
  );
}

export function XPGem({ size = 22, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={className} aria-hidden>
      <path d="M12 2 21 8.5 17.5 21h-11L3 8.5Z" fill="#16A34A" />
      <path d="M12 2 21 8.5 12 11 3 8.5Z" fill="#4ADE80" />
      <path d="M12 11 17.5 21h-11Z" fill="#15803D" />
    </svg>
  );
}

export function CreditCoin({ size = 20, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={className} aria-hidden>
      <circle cx="12" cy="12" r="10" fill="#F5B400" />
      <circle cx="12" cy="12" r="7.2" fill="#FFD54A" stroke="#E0A100" strokeWidth="1.2" />
      <path d="M10 8.5v7M10 12l4-3.5M10.8 11.4 14 15.5" stroke="#9A6B00" strokeWidth="1.8" strokeLinecap="round" fill="none" />
    </svg>
  );
}

const tierStyles: Record<string, string> = {
  bronze: "from-amber-700 via-orange-400 to-amber-600",
  silver: "from-slate-500 via-slate-200 to-slate-400",
  gold: "from-yellow-600 via-yellow-300 to-amber-500",
  emerald: "from-brand-800 via-brand-400 to-emerald-600",
};

export function BadgeMedal({ icon, tier, earned, size = 72 }: { icon: string; tier: string; earned: boolean; size?: number }) {
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <div className={cn("absolute inset-0 rounded-[30%] rotate-45 bg-gradient-to-br shadow-lift", earned ? tierStyles[tier] : "from-slate-200 to-slate-300")} />
      <div className={cn("absolute inset-[14%] flex items-center justify-center rounded-full", earned ? "bg-ink text-white" : "bg-slate-100 text-slate-400")}>
        <DynIcon name={earned ? icon : "lock"} className="h-1/2 w-1/2" />
      </div>
    </div>
  );
}
