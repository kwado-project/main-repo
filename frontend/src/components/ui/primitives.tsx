"use client";
import { forwardRef, useEffect, useRef, useState } from "react";
import { animate, motion, useInView, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

export function Card({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("card", className)} {...p} />;
}

export function Badge({ className, tone = "green", ...p }: React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "green" | "gray" | "dark" | "amber" | "red" | "blue";
}) {
  const tones = {
    green: "bg-brand-50 text-brand-800 ring-brand-200",
    gray: "bg-slate-100 text-slate-700 ring-slate-200",
    dark: "bg-ink text-white ring-ink",
    amber: "bg-amber-50 text-amber-800 ring-amber-200",
    red: "bg-red-50 text-red-700 ring-red-200",
    blue: "bg-sky-50 text-sky-800 ring-sky-200",
  };
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset", tones[tone], className)} {...p} />;
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }>(
  function Input({ className, invalid, ...p }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "h-12 w-full rounded-xl border bg-white px-4 text-[15px] text-ink placeholder:text-slate-400 transition focus:outline-none focus:ring-4",
          invalid ? "border-red-400 focus:ring-red-100" : "border-line focus:border-brand-500 focus:ring-brand-100",
          className,
        )}
        {...p}
      />
    );
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...p }, ref) {
    return <textarea ref={ref} className={cn("w-full rounded-xl border border-line bg-white px-4 py-3 text-[15px] focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100", className)} {...p} />;
  },
);

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(function Select({ className, ...p }, ref) {
  return <select ref={ref} className={cn("h-11 w-full rounded-xl border border-line bg-white px-3 text-[15px] focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100", className)} {...p} />;
});

export function Label({ className, ...p }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("mb-1.5 block text-sm font-semibold text-ink", className)} {...p} />;
}

export function FieldError({ children }: { children?: React.ReactNode }) {
  if (!children) return null;
  return <p role="alert" className="mt-1.5 text-sm font-medium text-red-600">{children}</p>;
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)}
      className={cn("relative h-7 w-12 shrink-0 rounded-full transition", checked ? "bg-brand-600" : "bg-slate-300")}>
      <motion.span layout transition={{ type: "spring", stiffness: 500, damping: 32 }}
        className={cn("absolute top-1 h-5 w-5 rounded-full bg-white shadow", checked ? "right-1" : "left-1")} />
    </button>
  );
}

export function Progress({ value, className, barClassName, animateIn = true }: { value: number; className?: string; barClassName?: string; animateIn?: boolean }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-2.5 w-full overflow-hidden rounded-full bg-slate-100", className)} role="progressbar" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100}>
      <motion.div
        className={cn("relative h-full rounded-full bg-gradient-to-r from-brand-600 to-brand-400", barClassName)}
        initial={animateIn ? { width: 0 } : false}
        animate={{ width: `${v}%` }}
        transition={{ type: "spring", stiffness: 60, damping: 18 }}
      >
        <span className="absolute inset-x-1 top-0.5 h-[3px] rounded-full bg-white/30" />
      </motion.div>
    </div>
  );
}

export function Ring({ value, size = 72, stroke = 8, children, color = "#16A34A", track = "#E5E7EB" }: {
  value: number; size?: number; stroke?: number; children?: React.ReactNode; color?: string; track?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
        <motion.circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - Math.min(100, value) / 100) }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }} />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">{children}</div>
    </div>
  );
}

export function CountUp({ value, duration = 1, className, format = (n: number) => Math.round(n).toLocaleString("en-NG") }: {
  value: number; duration?: number; className?: string; format?: (n: number) => string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const prev = useRef(0);
  useEffect(() => {
    if (!inView || !ref.current) return;
    if (reduce) { ref.current.textContent = format(value); prev.current = value; return; }
    const controls = animate(prev.current, value, {
      duration, ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => { if (ref.current) ref.current.textContent = format(v); },
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, inView, duration, format, reduce]);
  return <span ref={ref} className={className}>{format(0)}</span>;
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-xl bg-slate-200/70", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/60 to-transparent" />
    </div>
  );
}

export function EmptyState({ icon: Icon, title, body, action }: { icon: any; title: string; body?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="relative mb-4">
        <div className="absolute inset-0 scale-150 rounded-full bg-brand-100 blur-xl" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-brand-600 shadow-card ring-1 ring-line">
          <Icon className="h-7 w-7" />
        </div>
      </div>
      <h3 className="text-lg font-bold">{title}</h3>
      {body && <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, className }: {
  tabs: { value: T; label: string }[]; value: T; onChange: (v: T) => void; className?: string;
}) {
  return (
    <div role="tablist" className={cn("inline-flex rounded-xl bg-slate-100 p-1", className)}>
      {tabs.map((t) => (
        <button key={t.value} role="tab" aria-selected={value === t.value} onClick={() => onChange(t.value)}
          className={cn("relative rounded-lg px-3.5 py-1.5 text-sm font-semibold transition", value === t.value ? "text-ink" : "text-muted hover:text-ink")}>
          {value === t.value && <motion.span layoutId={`tab-${tabs.map((x) => x.value).join("")}`} className="absolute inset-0 rounded-lg bg-white shadow-card" transition={{ type: "spring", stiffness: 500, damping: 35 }} />}
          <span className="relative">{t.label}</span>
        </button>
      ))}
    </div>
  );
}

export function Avatar({ name, color = "#16A34A", size = 36, className }: { name: string; color?: string; size?: number; className?: string }) {
  const initials = (name || "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <span className={cn("inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white ring-2 ring-white", className)}
      style={{ width: size, height: size, background: color, fontSize: size * 0.38 }} aria-hidden>
      {initials}
    </span>
  );
}

export function useMounted() {
  const [m, setM] = useState(false);
  useEffect(() => setM(true), []);
  return m;
}
