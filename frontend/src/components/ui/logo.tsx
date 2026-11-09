import Link from "next/link";
import { cn } from "@/lib/utils";

export function LogoMark({ className, size = 34 }: { className?: string; size?: number }) {
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} className={className} aria-hidden>
      <rect width="40" height="40" rx="12" fill="#16A34A" />
      <path d="M12 10v20M12 21l10-11M15.5 17.5 24 30" stroke="#fff" strokeWidth="4.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <circle cx="29" cy="12" r="3.2" fill="#BBF7D0" />
    </svg>
  );
}

export function Logo({ dark = false, className, href = "/" }: { dark?: boolean; className?: string; href?: string }) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2.5", className)} aria-label="Kwado AI home">
      <LogoMark />
      <span className={cn("text-lg font-extrabold tracking-tight", dark ? "text-white" : "text-ink")}>
        Kwado<span className="text-brand-500"> AI</span>
      </span>
    </Link>
  );
}
