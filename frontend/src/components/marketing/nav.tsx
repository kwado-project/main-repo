"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Menu, X } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { buttonClass } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const links = [
  { href: "#home", label: "Home" },
  { href: "#how", label: "How it works" },
  { href: "#exams", label: "Examinations" },
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
];

export function MarketingNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { me } = useAuth();

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 12);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
  }, [open]);

  return (
    <header className={cn("fixed inset-x-0 top-0 z-50 transition-all duration-300", scrolled || open ? "bg-white/85 shadow-[0_1px_0_#E5E7EB] backdrop-blur-xl" : "bg-transparent")}>
      <nav className="container flex h-16 items-center justify-between lg:h-[72px]" aria-label="Main">
        <Logo />
        <ul className="hidden items-center gap-1 lg:flex">
          {links.map((l) => (
            <li key={l.href}>
              <a href={l.href} className="rounded-lg px-3.5 py-2 text-[15px] font-medium text-ink/75 transition hover:bg-ink/5 hover:text-ink">{l.label}</a>
            </li>
          ))}
        </ul>
        <div className="hidden items-center gap-2 lg:flex">
          {me ? (
            <Link href="/app" className={buttonClass("primary", "md")}>Go to dashboard <ArrowRight className="h-4 w-4" /></Link>
          ) : (
            <>
              <Link href="/login" className={buttonClass("ghost", "md")}>Login</Link>
              <Link href="/register" className={buttonClass("primary", "md")}>Get Started</Link>
            </>
          )}
        </div>
        <button className="relative z-50 -mr-2 rounded-xl p-2.5 lg:hidden" onClick={() => setOpen(!open)} aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}>
          <AnimatePresence mode="wait" initial={false}>
            <motion.span key={open ? "x" : "m"} initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.15 }} className="block">
              {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </motion.span>
          </AnimatePresence>
        </button>
      </nav>
      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-x-0 bottom-0 top-16 z-40 flex flex-col bg-white px-5 pb-8 pt-4 lg:hidden"
            initial={{ opacity: 0, clipPath: "inset(0 0 100% 0)" }}
            animate={{ opacity: 1, clipPath: "inset(0 0 0% 0)" }}
            exit={{ opacity: 0, clipPath: "inset(0 0 100% 0)" }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          >
            <motion.ul className="flex flex-col" initial="h" animate="s" variants={{ s: { transition: { staggerChildren: 0.05, delayChildren: 0.1 } } }}>
              {links.map((l) => (
                <motion.li key={l.href} variants={{ h: { opacity: 0, y: 12 }, s: { opacity: 1, y: 0 } }}>
                  <a href={l.href} onClick={() => setOpen(false)} className="flex items-center justify-between border-b border-line py-4 text-xl font-bold">
                    {l.label} <ArrowRight className="h-5 w-5 text-brand-600" />
                  </a>
                </motion.li>
              ))}
            </motion.ul>
            <div className="mt-auto grid gap-3">
              {me ? (
                <Link href="/app" className={buttonClass("primary", "lg")}>Go to dashboard</Link>
              ) : (
                <>
                  <Link href="/register" className={buttonClass("primary", "lg")}>Get Started — it&apos;s free</Link>
                  <Link href="/login" className={buttonClass("secondary", "lg")}>Login</Link>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
