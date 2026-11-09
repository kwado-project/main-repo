"use client";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "dark" | "outline" | "danger" | "soft";
type Size = "sm" | "md" | "lg" | "icon";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "bg-brand-600 text-white shadow-press hover:bg-brand-700 active:translate-y-px active:shadow-none",
  secondary: "bg-white text-ink border border-line shadow-card hover:border-brand-300 hover:bg-brand-50",
  ghost: "text-ink hover:bg-ink/5",
  dark: "bg-ink text-white shadow-press hover:bg-ink-soft active:translate-y-px",
  outline: "border-2 border-brand-600 text-brand-700 hover:bg-brand-50",
  danger: "bg-red-600 text-white shadow-press hover:bg-red-700",
  soft: "bg-brand-50 text-brand-800 hover:bg-brand-100",
};
const sizes: Record<Size, string> = {
  sm: "h-9 px-3.5 text-sm rounded-xl gap-1.5",
  md: "h-11 px-5 text-[15px] rounded-xl gap-2",
  lg: "h-14 px-7 text-base rounded-2xl gap-2.5",
  icon: "h-10 w-10 rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", size = "md", loading, disabled, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex select-none items-center justify-center font-semibold transition-all duration-150 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

export function buttonClass(variant: Variant = "primary", size: Size = "md", className?: string) {
  return cn(
    "inline-flex select-none items-center justify-center font-semibold transition-all duration-150",
    variants[variant],
    sizes[size],
    className,
  );
}
