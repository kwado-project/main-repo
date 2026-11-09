"use client";
import { useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function OTPInput({ value, onChange, onComplete, invalid, disabled, length = 6 }: {
  value: string; onChange: (v: string) => void; onComplete?: (v: string) => void; invalid?: boolean; disabled?: boolean; length?: number;
}) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length }, (_, i) => value[i] ?? "");

  const set = (next: string) => {
    const clean = next.replace(/\D/g, "").slice(0, length);
    onChange(clean);
    if (clean.length === length) onComplete?.(clean);
    return clean;
  };

  return (
    <motion.div
      className="flex justify-center gap-2 sm:gap-3"
      animate={invalid ? { x: [0, -10, 10, -6, 6, 0] } : { x: 0 }}
      transition={{ duration: 0.4 }}
      role="group"
      aria-label="Verification code"
    >
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el; }}
          value={d}
          disabled={disabled}
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          aria-label={`Digit ${i + 1}`}
          maxLength={length}
          autoFocus={i === 0}
          onFocus={(e) => e.currentTarget.select()}
          onChange={(e) => {
            const raw = e.target.value.replace(/\D/g, "");
            if (!raw) return;
            if (raw.length > 1) {
              // paste or SMS autofill into any box
              const clean = set(value.slice(0, i) + raw);
              refs.current[Math.min(clean.length, length - 1)]?.focus();
              return;
            }
            const arr = digits.slice();
            arr[i] = raw;
            set(arr.join(""));
            if (i < length - 1) refs.current[i + 1]?.focus();
          }}
          onKeyDown={(e) => {
            if (e.key === "Backspace") {
              e.preventDefault();
              const arr = digits.slice();
              if (arr[i]) { arr[i] = ""; set(arr.join("")); }
              else if (i > 0) { arr[i - 1] = ""; set(arr.join("")); refs.current[i - 1]?.focus(); }
            } else if (e.key === "ArrowLeft" && i > 0) refs.current[i - 1]?.focus();
            else if (e.key === "ArrowRight" && i < length - 1) refs.current[i + 1]?.focus();
          }}
          onPaste={(e) => {
            e.preventDefault();
            const clean = set(e.clipboardData.getData("text"));
            refs.current[Math.min(clean.length, length - 1)]?.focus();
          }}
          className={cn(
            "h-14 w-11 rounded-xl border-2 bg-white text-center text-2xl font-bold text-ink transition sm:h-16 sm:w-14",
            "focus:outline-none focus:ring-4",
            invalid ? "border-red-400 focus:ring-red-100" : d ? "border-brand-500 focus:ring-brand-100" : "border-line focus:border-brand-500 focus:ring-brand-100",
          )}
        />
      ))}
    </motion.div>
  );
}
