"use client";
import { useEffect } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { CheckCircle2, Snowflake } from "lucide-react";
import { Badge, Progress, Ring, Skeleton, Tabs } from "@/components/ui/primitives";
import { BadgeMedal, DynIcon, Flame, XPGem, fireConfetti } from "@/components/ui/fun";
import { api } from "@/lib/api";
import { cn, fmtDate } from "@/lib/utils";
import { useState } from "react";

export default function AchievementsPage() {
  const { data: g } = useSWR<any>("/gamification/summary");
  const { data: badges, mutate } = useSWR<any[]>("/gamification/badges");
  const { data: missions } = useSWR<any[]>("/gamification/missions");
  const { data: xp } = useSWR<any[]>("/gamification/xp-history");
  const [period, setPeriod] = useState<"daily" | "weekly">("daily");

  useEffect(() => {
    if (badges?.some((b) => b.earned && !b.seen)) {
      fireConfetti({ big: true });
      api("/gamification/badges/seen", { method: "POST" }).then(() => mutate());
    }
  }, [badges, mutate]);

  const levelPct = g ? ((g.xp - g.level_floor) / (g.level_ceiling - g.level_floor)) * 100 : 0;
  const max = Math.max(1, ...(g?.heatmap?.map((d: any) => d.xp) ?? [1]));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold sm:text-3xl">Achievements</h1>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card flex items-center gap-5 p-5">
          <Ring value={levelPct} size={96} stroke={9}><div className="text-center"><p className="text-[10px] font-bold uppercase text-muted">Level</p><p className="text-3xl font-extrabold leading-none">{g?.level ?? "–"}</p></div></Ring>
          <div><p className="flex items-center gap-1.5 text-2xl font-extrabold"><XPGem /> {g?.xp?.toLocaleString() ?? "–"}</p><p className="text-sm text-muted">{g ? `${g.level_ceiling - g.xp} XP to level ${g.level + 1}` : ""}</p></div>
        </div>
        <div className="card flex items-center gap-4 bg-gradient-to-br from-orange-50 to-white p-5">
          <Flame size={64} active={!!g?.streak?.active_today} />
          <div><p className="text-3xl font-extrabold">{g?.streak?.current ?? 0} days</p><p className="text-sm text-muted">Longest: {g?.streak?.longest ?? 0} days</p>
            <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-sky-700"><Snowflake className="h-3.5 w-3.5" /> {g?.streak?.freezes ?? 0} streak freeze{g?.streak?.freezes === 1 ? "" : "s"} · earn one every 7 days</p></div>
        </div>
        <div className="card p-5">
          <p className="text-sm font-bold">Last 4 weeks</p>
          <div className="mt-3 grid grid-cols-7 gap-1.5">
            {g?.heatmap?.map((d: any) => (
              <div key={d.date} title={`${fmtDate(d.date)}: ${d.xp} XP`} className="aspect-square rounded-md" style={{ background: d.xp ? `rgba(22,163,74,${0.25 + 0.75 * (d.xp / max)})` : "#F1F5F9" }} />
            )) ?? <Skeleton className="col-span-7 h-28" />}
          </div>
        </div>
      </section>

      <section className="card p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Missions</h2>
          <Tabs value={period} onChange={setPeriod} tabs={[{ value: "daily", label: "Daily" }, { value: "weekly", label: "Weekly" }]} />
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {missions?.filter((m) => m.period === period).map((m) => (
            <div key={m.id} className={cn("flex items-center gap-4 rounded-2xl border p-4", m.completed ? "border-brand-200 bg-brand-50" : "border-line")}>
              <span className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-xl", m.completed ? "bg-brand-600 text-white" : "bg-slate-100")}>{m.completed ? <CheckCircle2 className="h-6 w-6" /> : <DynIcon name={m.icon} className="h-6 w-6" />}</span>
              <div className="min-w-0 flex-1">
                <div className="flex justify-between gap-2"><p className="font-semibold">{m.title}</p><Badge tone={m.completed ? "green" : "gray"}>+{m.xp_reward} XP</Badge></div>
                <div className="mt-2 flex items-center gap-2"><Progress value={(m.progress / m.target) * 100} className="h-2" /><span className="text-xs font-semibold text-muted">{m.progress}/{m.target}</span></div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-bold">Badges <span className="text-sm font-semibold text-muted">· {badges?.filter((b) => b.earned).length ?? 0}/{badges?.length ?? 0}</span></h2>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {badges?.map((b, i) => (
            <motion.div key={b.slug} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
              className={cn("card flex flex-col items-center p-5 text-center", !b.earned && "bg-slate-50")}>
              <motion.div whileHover={b.earned ? { rotate: [0, -8, 8, 0], scale: 1.08 } : {}}><BadgeMedal icon={b.icon} tier={b.tier} earned={b.earned} size={76} /></motion.div>
              <p className="mt-4 font-bold">{b.name}</p>
              <p className="mt-1 text-xs text-muted">{b.description}</p>
              <p className="mt-2 text-xs font-semibold">{b.earned ? <span className="text-brand-700">Earned {fmtDate(b.earned_at)}</span> : <span className="text-muted">+{b.xp_reward} XP</span>}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="card p-5">
        <h2 className="text-lg font-bold">Recent XP</h2>
        <ul className="mt-3 divide-y divide-line">
          {xp?.length === 0 && <li className="py-6 text-center text-sm text-muted">Complete a lesson or quiz to start earning XP.</li>}
          {xp?.map((x, i) => <li key={i} className="flex justify-between py-2.5 text-sm"><span>{x.reason}</span><span className="font-bold text-brand-700">+{x.amount} XP</span></li>)}
        </ul>
      </section>
    </div>
  );
}
