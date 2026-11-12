"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { AnimatePresence, motion } from "framer-motion";
import {
  Award, Bell, BookOpen, Bot, ChevronDown, CirclePlus, FileUp, Gift, GraduationCap, Home, LayoutDashboard, LogOut,
  Map, Menu, Settings, Shield, Sparkles, Swords, Trophy, Wallet,
} from "lucide-react";
import { ProductTour, TOUR_EVENT, startTour } from "@/components/app/tour";
import { Logo } from "@/components/ui/logo";
import { Avatar, Skeleton } from "@/components/ui/primitives";
import { CreditCoin, Flame, XPGem } from "@/components/ui/fun";
import { Drawer } from "@/components/ui/overlay";
import { api } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth";
import { cn, fmtDate } from "@/lib/utils";

const NAV = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/app/learn", label: "Learn", icon: BookOpen },
  { href: "/app/practice", label: "Practice", icon: Swords },
  { href: "/app/tutor", label: "AI Tutor", icon: Bot },
  { href: "/app/roadmap", label: "Roadmap", icon: Map },
  { href: "/app/leaderboard", label: "Leaderboard", icon: Trophy },
  { href: "/app/achievements", label: "Achievements", icon: Award },
  { href: "/app/materials", label: "Materials", icon: FileUp },
  { href: "/app/wallet", label: "Wallet", icon: Wallet },
  { href: "/app/referrals", label: "Refer & earn", icon: Gift },
];
const BOTTOM = [NAV[0], NAV[1], NAV[2], NAV[3], NAV[4]];

/** data-tour key for a nav link, e.g. "/app/learn" → "learn" (used by the first-visit tour). */
const tourKey = (href: string) => href.split("/")[2] || "home";

function isActive(path: string, href: string) {
  return href === "/app" ? path === "/app" : path.startsWith(href);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const me = useRequireAuth();
  const path = usePathname();
  const router = useRouter();
  const [drawer, setDrawer] = useState(false);
  const immersive = /^\/app\/(quiz|lesson)\//.test(path);

  useEffect(() => setDrawer(false), [path]);
  useEffect(() => {
    const close = () => setDrawer(false);
    window.addEventListener(TOUR_EVENT, close);
    return () => window.removeEventListener(TOUR_EVENT, close);
  }, []);
  useEffect(() => {
    // Quizzes and lessons stay reachable mid-onboarding (the diagnostic runs inside onboarding).
    if (me && !immersive && me.role === "student" && !me.profile.onboarding_completed && me.student_exams.every((x) => x.onboarding_step !== "done")) {
      router.replace("/onboarding");
    }
  }, [me, router, immersive]);

  if (!me) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas">
        <div className="flex flex-col items-center gap-4"><Logo /><Skeleton className="h-2 w-40" /></div>
      </div>
    );
  }
  if (immersive) return <div className="min-h-dvh bg-canvas">{children}</div>;

  return (
    <div className="min-h-dvh bg-canvas">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-line bg-white lg:flex">
        <div className="flex h-[72px] items-center px-6"><Logo href="/app" /></div>
        <SidebarNav path={path} role={me.role} />
      </aside>

      <div className="lg:pl-[248px]">
        <TopBar onMenu={() => setDrawer(true)} />
        <main className="mx-auto w-full max-w-[1180px] px-4 pb-28 pt-5 sm:px-6 lg:px-8 lg:pb-12 lg:pt-8">
          <motion.div key={path} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            {children}
          </motion.div>
        </main>
      </div>

      {/* mobile bottom nav */}
      <nav className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white/95 backdrop-blur-xl lg:hidden" aria-label="Primary">
        <ul className="mx-auto grid max-w-lg grid-cols-5">
          {BOTTOM.map((n) => {
            const active = isActive(path, n.href);
            return (
              <li key={n.href}>
                <Link href={n.href} data-tour={tourKey(n.href)} className="relative flex flex-col items-center gap-0.5 pb-1 pt-2.5 text-[11px] font-semibold" aria-current={active ? "page" : undefined}>
                  {active && <motion.span layoutId="bottom-pill" className="absolute top-1 h-8 w-14 rounded-full bg-brand-50" transition={{ type: "spring", stiffness: 500, damping: 35 }} />}
                  <n.icon className={cn("relative h-[22px] w-[22px]", active ? "text-brand-700" : "text-slate-400")} strokeWidth={active ? 2.4 : 2} />
                  <span className={cn("relative", active ? "text-brand-800" : "text-slate-500")}>{n.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <Drawer open={drawer} onClose={() => setDrawer(false)} side="left" title="Menu">
        <div className="flex h-16 items-center px-5"><Logo href="/app" /></div>
        <SidebarNav path={path} role={me.role} />
      </Drawer>
      <ProductTour />
    </div>
  );
}

function SidebarNav({ path, role }: { path: string; role: string }) {
  const { signOut } = useAuth();
  const router = useRouter();
  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-3 pb-4">
      <ul className="space-y-0.5">
        {NAV.map((n) => {
          const active = isActive(path, n.href);
          return (
            <li key={n.href}>
              <Link href={n.href} data-tour={tourKey(n.href)} aria-current={active ? "page" : undefined}
                className={cn("relative flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] font-semibold transition", active ? "text-brand-800" : "text-slate-600 hover:bg-slate-50 hover:text-ink")}>
                {active && <motion.span layoutId="side-pill" className="absolute inset-0 rounded-xl bg-brand-50 ring-1 ring-brand-100" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
                <n.icon className={cn("relative h-5 w-5", active && "text-brand-600")} />
                <span className="relative">{n.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="mt-auto space-y-0.5 border-t border-line pt-3">
        {role !== "student" && (
          <Link href="/admin" className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] font-semibold text-slate-600 hover:bg-slate-50"><Shield className="h-5 w-5" /> Admin console</Link>
        )}
        <Link href="/app/profile" className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] font-semibold text-slate-600 hover:bg-slate-50"><Settings className="h-5 w-5" /> Settings</Link>
        <button onClick={startTour} className="flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] font-semibold text-slate-600 hover:bg-slate-50"><Sparkles className="h-5 w-5" /> Take the tour</button>
        <button onClick={async () => { await signOut(); router.replace("/"); }} className="flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] font-semibold text-slate-600 hover:bg-red-50 hover:text-red-700"><LogOut className="h-5 w-5" /> Log out</button>
      </div>
    </div>
  );
}

function TopBar({ onMenu }: { onMenu: () => void }) {
  const { me } = useAuth();
  const { data: g } = useSWR<any>("/gamification/summary");
  const { data: wallet } = useSWR<any>("/wallet", { refreshInterval: 60_000 });
  if (!me) return null;
  const balance = wallet?.balance ?? me.balance;
  return (
    <header className="sticky top-0 z-30 border-b border-line/80 bg-canvas/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1180px] items-center gap-2 px-4 sm:px-6 lg:h-[72px] lg:px-8">
        <button onClick={onMenu} className="-ml-1.5 rounded-xl p-2 lg:hidden" aria-label="Open menu"><Menu className="h-6 w-6" /></button>
        <ExamSwitcher />
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <Link href="/app/achievements" className="hidden items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-sm font-bold shadow-card ring-1 ring-line sm:flex" aria-label="Streak">
            <Flame size={20} active={!!g?.streak?.active_today} />{g?.streak?.current ?? 0}
          </Link>
          <Link href="/app/achievements" className="flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-sm font-bold shadow-card ring-1 ring-line" aria-label="XP" id="xp-counter" data-tour="xp">
            <XPGem size={18} /><span className="tabular-nums">{(g?.xp ?? me.profile.total_xp).toLocaleString()}</span>
          </Link>
          <Link href="/app/wallet" data-tour="credits" className="flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-sm font-bold text-white shadow-card" aria-label={`Wallet: ${balance} credits`}>
            <CreditCoin size={18} /><span className="tabular-nums">{balance.toLocaleString()}</span>
          </Link>
          <Notifications />
          <ProfileMenu />
        </div>
      </div>
    </header>
  );
}

function ExamSwitcher() {
  const { me, reload } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const on = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", on);
    return () => document.removeEventListener("mousedown", on);
  }, []);
  if (!me) return null;
  const exams = me.student_exams.filter((x) => x.onboarding_step === "done" || x.id === me.profile.active_student_exam);
  const active = exams.find((x) => x.id === me.profile.active_student_exam) ?? exams[0];
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} data-tour="exam" className="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-white" aria-expanded={open} aria-haspopup="menu">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg text-white" style={{ background: active?.examination.color ?? "#16A34A" }}><GraduationCap className="h-4 w-4" /></span>
        <span className="hidden text-left sm:block">
          <span className="block text-sm font-bold leading-tight">{active?.examination.name ?? "Choose exam"}</span>
          {active?.days_left != null && <span className="block text-xs text-muted">{active.days_left} days left</span>}
        </span>
        <ChevronDown className="h-4 w-4 text-muted" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: -6, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6 }}
            className="absolute left-0 top-12 z-50 w-72 rounded-2xl bg-white p-2 shadow-lift ring-1 ring-line" role="menu">
            <p className="px-3 py-2 text-xs font-bold uppercase tracking-wider text-muted">Your examinations</p>
            {exams.map((x) => (
              <button key={x.id} role="menuitem" onClick={async () => { await api(`/student-exams/${x.id}/activate`, { method: "POST" }); await reload(); setOpen(false); window.location.reload(); }}
                className={cn("flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-slate-50", x.id === active?.id && "bg-brand-50")}>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg text-white" style={{ background: x.examination.color }}><GraduationCap className="h-4 w-4" /></span>
                <span className="flex-1"><span className="block text-sm font-bold">{x.examination.name}</span><span className="block text-xs text-muted">{x.exam_date ? fmtDate(x.exam_date) : "Date not set"}</span></span>
              </button>
            ))}
            <Link href="/onboarding?add=1" className="mt-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50"><CirclePlus className="h-5 w-5" /> Add another examination</Link>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Notifications() {
  const [open, setOpen] = useState(false);
  const { data, mutate } = useSWR<any>("/notifications", { refreshInterval: 90_000 });
  const router = useRouter();
  const unread = data?.unread ?? 0;
  return (
    <>
      <button onClick={() => setOpen(true)} className="relative flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-card ring-1 ring-line" aria-label={`Notifications, ${unread} unread`}>
        <Bell className="h-5 w-5" />
        {unread > 0 && <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-bold text-white ring-2 ring-canvas">{unread > 9 ? "9+" : unread}</span>}
      </button>
      <Drawer open={open} onClose={() => setOpen(false)} title="Notifications">
        <div className="flex items-center justify-between border-b border-line p-5">
          <h2 className="text-lg font-bold">Notifications</h2>
          {unread > 0 && <button onClick={async () => { await api("/notifications/read", { method: "POST", json: {} }); mutate(); }} className="text-sm font-semibold text-brand-700">Mark all read</button>}
        </div>
        <ul className="divide-y divide-line">
          {!data?.items?.length && <li className="p-8 text-center text-sm text-muted">You&apos;re all caught up.</li>}
          {data?.items?.map((n: any) => (
            <li key={n.id}>
              <button onClick={async () => { if (!n.read) await api("/notifications/read", { method: "POST", json: { ids: [n.id] } }); mutate(); setOpen(false); if (n.link) router.push(n.link); }}
                className={cn("flex w-full gap-3 p-4 text-left hover:bg-slate-50", !n.read && "bg-brand-50/40")}>
                <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", n.read ? "bg-transparent" : "bg-brand-600")} />
                <span><span className="block text-sm font-bold">{n.title}</span>{n.body && <span className="block text-sm text-muted">{n.body}</span>}<span className="mt-1 block text-xs text-slate-400">{fmtDate(n.created_at, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span></span>
              </button>
            </li>
          ))}
        </ul>
      </Drawer>
    </>
  );
}

function ProfileMenu() {
  const { me, signOut } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const on = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", on);
    return () => document.removeEventListener("mousedown", on);
  }, []);
  if (!me) return null;
  const name = me.profile.display_name || me.full_name || me.email;
  return (
    <div className="relative hidden sm:block" ref={ref}>
      <button onClick={() => setOpen(!open)} aria-label="Account menu" aria-expanded={open}><Avatar name={name} color={me.profile.avatar_color} size={40} /></button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="absolute right-0 top-12 z-50 w-60 rounded-2xl bg-white p-2 shadow-lift ring-1 ring-line">
            <div className="px-3 py-2"><p className="truncate font-bold">{name}</p><p className="truncate text-xs text-muted">{me.email}</p></div>
            <Link href="/app/profile" className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-semibold hover:bg-slate-50"><Settings className="h-4 w-4" /> Profile & settings</Link>
            <button onClick={() => { setOpen(false); startTour(); }} className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-semibold hover:bg-slate-50"><Sparkles className="h-4 w-4" /> Take the tour</button>
            {me.role !== "student" && <Link href="/admin" className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-semibold hover:bg-slate-50"><LayoutDashboard className="h-4 w-4" /> Admin console</Link>}
            <button onClick={async () => { await signOut(); router.replace("/"); }} className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"><LogOut className="h-4 w-4" /> Log out</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
