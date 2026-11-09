"use client";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { Crown, EyeOff, Trophy } from "lucide-react";
import { Avatar, EmptyState, Select, Skeleton, Tabs } from "@/components/ui/primitives";
import { XPGem } from "@/components/ui/fun";
import { cn } from "@/lib/utils";

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<"daily" | "weekly" | "subject">("weekly");
  const { data: progress } = useSWR<any[]>("/assessments/progress");
  const [subject, setSubject] = useState("");
  const sid = subject || (progress?.[0]?.subject.id ?? "");
  const { data } = useSWR<any>(`/gamification/leaderboard?period=${period}${period === "subject" ? `&subject=${sid}` : ""}`, { refreshInterval: 30000 });
  const top = data?.entries?.slice(0, 3) ?? [];
  const rest = data?.entries?.slice(3) ?? [];
  const podium = [top[1], top[0], top[2]];

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div><h1 className="text-2xl font-extrabold sm:text-3xl">Leaderboard</h1><p className="mt-1 text-muted">Earn XP to climb. Resets {period === "daily" ? "every midnight" : "every Monday"}.</p></div>
        <Tabs value={period} onChange={setPeriod} tabs={[{ value: "daily", label: "Today" }, { value: "weekly", label: "This week" }, { value: "subject", label: "By subject" }]} />
      </div>
      {period === "subject" && (
        <Select className="mt-4 sm:w-64" value={sid} onChange={(e) => setSubject(e.target.value)}>{progress?.map((p) => <option key={p.subject.id} value={p.subject.id}>{p.subject.name}</option>)}</Select>
      )}

      {!data ? <Skeleton className="mt-8 h-64" /> : data.entries.length === 0 ? (
        <div className="card mt-8"><EmptyState icon={Trophy} title="No one on the board yet" body="Be the first! Complete a quiz or lesson to earn XP." /></div>
      ) : (
        <>
          <div className="mt-10 flex items-end justify-center gap-3 sm:gap-6">
            {podium.map((e: any, i: number) => e ? (
              <motion.div key={e.rank} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: [0.15, 0, 0.3][i] }} className="flex w-24 flex-col items-center sm:w-32">
                {e.rank === 1 && <Crown className="mb-1 h-7 w-7 text-gold" />}
                <Avatar name={e.name} color={e.avatar_color} size={e.rank === 1 ? 64 : 52} className={cn(e.is_me && "ring-brand-500")} />
                <p className="mt-2 w-full truncate text-center text-sm font-bold">{e.is_me ? "You" : e.name}</p>
                <p className="flex items-center gap-1 text-xs font-semibold text-muted"><XPGem size={12} />{e.xp}</p>
                <div className={cn("mt-2 flex w-full items-start justify-center rounded-t-2xl pt-3 text-2xl font-extrabold text-white", e.rank === 1 ? "h-28 bg-brand-600" : e.rank === 2 ? "h-20 bg-brand-500" : "h-14 bg-brand-400")}>{e.rank}</div>
              </motion.div>
            ) : <div key={i} className="w-24 sm:w-32" />)}
          </div>
          <ol className="card divide-y divide-line">
            {rest.map((e: any, i: number) => (
              <motion.li key={e.rank} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.02 }} className={cn("flex items-center gap-3 px-4 py-3", e.is_me && "bg-brand-50")}>
                <span className="w-6 text-center text-sm font-bold text-muted">{e.rank}</span>
                <Avatar name={e.name} color={e.avatar_color} size={36} />
                <span className="flex-1 truncate font-semibold">{e.is_me ? "You" : e.name} <span className="text-xs font-medium text-muted">· L{e.level}</span></span>
                <span className="flex items-center gap-1 font-bold"><XPGem size={16} />{e.xp}</span>
              </motion.li>
            ))}
          </ol>
          {!data.me && <p className="mt-4 text-center text-sm text-muted">You&apos;re not on this board yet — earn some XP to join in.</p>}
        </>
      )}
      <p className="mt-6 flex items-center justify-center gap-1.5 text-xs text-muted"><EyeOff className="h-4 w-4" /> Control how you appear in <Link href="/app/profile#privacy" className="font-semibold text-brand-700">privacy settings</Link>.</p>
    </div>
  );
}
