"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Activity, ArrowLeft, Bot, BookMarked, Coins, CreditCard, FileQuestion, FileText, Gift, GraduationCap, Layers,
  LayoutDashboard, Megaphone, Menu, Microscope, Receipt, ScrollText, Settings, Users,
} from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { Badge, Skeleton } from "@/components/ui/primitives";
import { Drawer } from "@/components/ui/overlay";
import { useRequireAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const ADMIN_NAV = [
  { group: "Overview", items: [{ href: "/admin", label: "Analytics", icon: LayoutDashboard, staff: true }] },
  { group: "Content", items: [
    { href: "/admin/questions", label: "Question bank", icon: FileQuestion, staff: true },
    { href: "/admin/research", label: "Past-question research", icon: Microscope, staff: true },
    { href: "/admin/examinations", label: "Examinations", icon: GraduationCap, staff: true },
    { href: "/admin/exam-subjects", label: "Exam rules", icon: Layers, staff: true },
    { href: "/admin/subjects", label: "Subjects", icon: BookMarked, staff: true },
    { href: "/admin/topics", label: "Topics", icon: Layers, staff: true },
    { href: "/admin/lessons", label: "Lessons", icon: FileText, staff: true },
    { href: "/admin/learning-paths", label: "Learning paths", icon: Activity, staff: true },
  ] },
  { group: "Business", items: [
    { href: "/admin/users", label: "Students & users", icon: Users },
    { href: "/admin/payments", label: "Payments", icon: CreditCard },
    { href: "/admin/transactions", label: "Wallet ledger", icon: Receipt },
    { href: "/admin/referral-rewards", label: "Referral rewards", icon: Gift },
    { href: "/admin/packages", label: "Credit packages", icon: Coins },
    { href: "/admin/pricing", label: "Activity pricing", icon: Coins },
  ] },
  { group: "System", items: [
    { href: "/admin/ai-config", label: "AI configuration", icon: Bot },
    { href: "/admin/materials", label: "Uploaded materials", icon: FileText },
    { href: "/admin/broadcast", label: "Notifications", icon: Megaphone },
    { href: "/admin/audit-logs", label: "Audit log", icon: ScrollText },
    { href: "/admin/settings", label: "System settings", icon: Settings },
  ] },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const me = useRequireAuth({ role: "staff" });
  const path = usePathname();
  const [open, setOpen] = useState(false);
  if (!me || me.role === "student") return <div className="flex min-h-dvh items-center justify-center"><Skeleton className="h-8 w-48" /></div>;
  const isAdmin = me.role === "admin";
  const nav = (
    <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-6">
      {ADMIN_NAV.map((g) => {
        const items = g.items.filter((i: any) => isAdmin || i.staff);
        if (!items.length) return null;
        return (
          <div key={g.group}>
            <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-white/40">{g.group}</p>
            {items.map((i) => {
              const active = i.href === "/admin" ? path === "/admin" : path.startsWith(i.href);
              return (
                <Link key={i.href} href={i.href} onClick={() => setOpen(false)} className={cn("flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition", active ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white")}>
                  <i.icon className={cn("h-4 w-4", active && "text-brand-400")} /> {i.label}
                </Link>
              );
            })}
          </div>
        );
      })}
      <Link href="/app" className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold text-white/60 hover:text-white"><ArrowLeft className="h-4 w-4" /> Student app</Link>
    </nav>
  );
  return (
    <div className="min-h-dvh bg-canvas">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col bg-ink-deep lg:flex">
        <div className="flex h-16 items-center gap-2 px-6"><Logo dark href="/admin" /></div>
        {nav}
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-white/90 px-4 backdrop-blur lg:px-8">
          <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open admin menu"><Menu className="h-6 w-6" /></button>
          <span className="font-bold">Admin console</span>
          <Badge tone={isAdmin ? "dark" : "blue"} className="ml-auto">{isAdmin ? "Administrator" : "Content manager"}</Badge>
          <span className="hidden text-sm text-muted sm:inline">{me.email}</span>
        </header>
        <main className="mx-auto max-w-[1280px] px-4 py-6 lg:px-8 lg:py-8">{children}</main>
      </div>
      <Drawer open={open} onClose={() => setOpen(false)} side="left" className="bg-ink-deep" title="Admin menu">
        <div className="flex h-16 items-center px-5"><Logo dark href="/admin" /></div>{nav}
      </Drawer>
    </div>
  );
}
