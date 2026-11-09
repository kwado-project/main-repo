"use client";
import Link from "next/link";
import useSWR from "swr";
import { motion } from "framer-motion";
import {
  ArrowRight, BookOpen, Bot, CalendarClock, CheckCircle2, ChevronRight, Lightbulb, Map, Plus, Sparkles, Swords,
  Target, TrendingUp, Trophy,
} from "lucide-react";
import { buttonClass } from "@/components/ui/button";
import { Badge, Card, CountUp, Progress, Ring, Skeleton } from "@/components/ui/primitives";
import { BadgeMedal, CreditCoin, DynIcon, Flame, XPGem } from "@/components/ui/fun";
import { useAuth } from "@/lib/auth";
import { cn, greeting } from "@/lib/utils";

const stagger = { show: { transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.45 } } };

const MOTIVATION = [
  "Small steps every day add up to big results.",
  "Every mistake is a lesson. Let's learn a few today.",
  "You're building the habit that passes exams.",
  "Focus on one weak topic today — that's how scores jump.",
];

export default function Dashboard() {
  const { me } = useAuth();
  const { data: g } = useSWR<any>("/gamification/summary");
  const { data: missions } = useSWR<any[]>("/gamification/missions");
  const { data: badges } = useSWR<any[]>("/gamification/badges");
  const { data: next } = useSWR<any>("/learning/continue");
  const { data: progress } = useSWR<any[]>("/assessments/progress");
  const { data: roadmap } = useSWR<any>("/roadmaps/current");
  const { data: wallet } = useSWR<any>("/wallet");
  const { data: recent } = useSWR<any>("/assessments/attempts?page_size=5");
  if (!me) return null;

  const se = me.student_exams.find((x) => x.id === me.profile.active_student_exam) ?? me.student_exams[0];
  const name = me.profile.display_name || me.full_name?.split(" ")[0] || "there";
  const motivation = MOTIVATION[new Date().getDate() % MOTIVATION.length];
  const levelPct = g ? ((g.xp - g.level_floor) / (g.level_ceiling - g.level_floor)) * 100 : 0;
  const todayPct = g ? Math.min(100, (g.today_xp / g.daily_goal_xp) * 100) : 0;

  const recs: { icon: any; text: string; href: string; tone: string }[] = [];
  const weakest = progress?.filter((p) => p.topics_practised > 0).sort((a, b) => a.mastery - b.mastery)[0];
  if (weakest) recs.push({ icon: Target, text: `You need more practice in ${weakest.subject.name} — mastery is ${weakest.mastery}%.`, href: `/app/learn/${weakest.subject.id}`, tone: "amber" });
  const lastTwo = recent?.results?.slice(0, 2);
  if (lastTwo?.length === 2 && lastTwo[0].score_percent && lastTwo[1].score_percent) {
    const diff = Math.round(Number(lastTwo[0].score_percent) - Number(lastTwo[1].score_percent));
    if (diff > 0) recs.push({ icon: TrendingUp, text: `Your latest score improved by ${diff}% — keep the momentum!`, href: "/app/practice", tone: "green" });
  }
  if (roadmap?.stats?.overdue) recs.push({ icon: CalendarClock, text: `You have ${roadmap.stats.overdue} overdue roadmap task${roadmap.stats.overdue > 1 ? "s" : ""}. Catch up in 15 minutes.`, href: "/app/roadmap", tone: "red" });
  if (se?.days_left != null && se.days_left <= 30) recs.push({ icon: Trophy, text: `${se.days_left} days to ${se.examination.name}. Time for full mock exams.`, href: "/app/practice", tone: "dark" });
  if (!progress?.some((p) => p.topics_practised > 0)) recs.push({ icon: Sparkles, text: "Take your first quiz to unlock personalised insights.", href: "/app/practice", tone: "green" });

  return (
    <motion.div initial="hidden" animate="show" variants={stagger} className="space-y-5 lg:space-y-6">
      {/* welcome */}
      <motion.section variants={item} className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-muted">{new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}</p>
          <h1 className="mt-1 text-2xl font-extrabold sm:text-3xl">{greeting()}, {name}!</h1>
          <p className="mt-1 text-muted">{motivation}</p>
        </div>
        <Link href="/app/practice" className={buttonClass("primary", "md", "w-full sm:w-auto")}><Swords className="h-4 w-4" /> Quick practice</Link>
      </motion.section>

      <div className="grid gap-5 lg:grid-cols-3 lg:gap-6">
        <div className="space-y-5 lg:col-span-2 lg:space-y-6">
          {/* continue learning — the obvious next action */}
          <motion.section variants={item}>
            <ContinueCard next={next} />
          </motion.section>

          {/* countdown + streak */}
          <div className="grid gap-5 sm:grid-cols-2">
            <motion.section variants={item} className="relative overflow-hidden rounded-2xl bg-ink p-5 text-white">
              <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full bg-brand-600/30 blur-2xl" />
              <div className="relative flex items-center gap-2 text-sm text-white/60"><CalendarClock className="h-4 w-4" /> {se?.examination.name ?? "No exam selected"}</div>
              {se?.days_left != null ? (
                <>
                  <div className="relative mt-2 flex items-end gap-2"><CountUp value={se.days_left} className="text-5xl font-extrabold tabular-nums" /><span className="mb-2 text-white/70">days to go</span></div>
                  <p className="relative text-sm text-white/60">{new Date(se.exam_date!).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</p>
                </>
              ) : (
                <Link href="/app/profile#exams" className="relative mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand-400">Set your exam date <ArrowRight className="h-4 w-4" /></Link>
              )}
              {roadmap?.stats && (
                <div className="relative mt-4">
                  <div className="flex justify-between text-xs text-white/60"><span>Roadmap progress</span><span>{roadmap.stats.completed}/{roadmap.stats.total}</span></div>
                  <Progress value={(roadmap.stats.completed / Math.max(1, roadmap.stats.total)) * 100} className="mt-1.5 h-2 bg-white/10" />
                </div>
              )}
            </motion.section>

            <motion.section variants={item} className="card p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Flame size={38} active={!!g?.streak?.active_today} />
                  <div><p className="text-3xl font-extrabold leading-none">{g?.streak?.current ?? 0}</p><p className="text-sm text-muted">day streak</p></div>
                </div>
                <Badge tone={g?.streak?.active_today ? "green" : "amber"}>{g?.streak?.active_today ? "Done today" : "Keep it alive"}</Badge>
              </div>
              <div className="mt-5 flex justify-between">
                {(g?.week ?? Array.from({ length: 7 }, () => ({ active: false }))).map((d: any, i: number) => {
                  const today = (new Date().getDay() + 6) % 7 === i;
                  return (
                    <div key={i} className="flex flex-col items-center gap-1.5">
                      <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2 + i * 0.05, type: "spring" }}
                        className={cn("flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold", d.active ? "bg-flame text-white" : today ? "border-2 border-dashed border-flame/60 text-flame" : "bg-slate-100 text-slate-400")}>
                        {d.active ? <CheckCircle2 className="h-4 w-4" /> : null}
                      </motion.span>
                      <span className={cn("text-[11px] font-semibold", today ? "text-ink" : "text-muted")}>{"MTWTFSS"[i]}</span>
                    </div>
                  );
                })}
              </div>
              <p className="mt-4 text-xs text-muted">Longest streak: <b className="text-ink">{g?.streak?.longest ?? 0} day{g?.streak?.longest === 1 ? "" : "s"}</b> · {g?.streak?.freezes ?? 0} streak freeze{g?.streak?.freezes === 1 ? "" : "s"}</p>
            </motion.section>
          </div>

          {/* daily missions */}
          <motion.section variants={item} className="card p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">Daily missions</h2>
              <Link href="/app/achievements" className="text-sm font-semibold text-brand-700">All missions</Link>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {!missions && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[74px]" />)}
              {missions?.filter((m) => m.period === "daily").map((m) => (
                <div key={m.id} className={cn("flex items-center gap-3 rounded-xl border p-3", m.completed ? "border-brand-200 bg-brand-50" : "border-line")}>
                  <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", m.completed ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600")}>
                    {m.completed ? <CheckCircle2 className="h-5 w-5" /> : <DynIcon name={m.icon} className="h-5 w-5" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2"><p className="truncate text-sm font-semibold">{m.title}</p><span className="shrink-0 text-xs font-bold text-brand-700">+{m.xp_reward} XP</span></div>
                    <div className="mt-1.5 flex items-center gap-2"><Progress value={(m.progress / m.target) * 100} className="h-1.5" /><span className="text-[11px] font-semibold text-muted">{m.progress}/{m.target}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>

          {/* subject progress */}
          <motion.section variants={item} className="card p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold">Subject progress</h2>
              <Link href="/app/learn" className="text-sm font-semibold text-brand-700">Open learning</Link>
            </div>
            <div className="mt-4 space-y-3">
              {!progress && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14" />)}
              {progress?.map((p) => (
                <Link key={p.subject.id} href={`/app/learn/${p.subject.id}`} className="group flex items-center gap-3 rounded-xl p-2 transition hover:bg-slate-50">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white" style={{ background: p.subject.color }}><DynIcon name={p.subject.icon} className="h-5 w-5" /></span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between"><p className="truncate font-semibold">{p.subject.name}</p><span className="text-sm font-bold">{p.mastery}%</span></div>
                    <div className="mt-1.5 flex items-center gap-3"><Progress value={p.mastery} className="h-2" /><span className="w-24 shrink-0 text-right text-xs text-muted">{p.level}</span></div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-brand-600" />
                </Link>
              ))}
            </div>
          </motion.section>
        </div>

        {/* right column */}
        <div className="space-y-5 lg:space-y-6">
          <motion.section variants={item} className="card p-5">
            <div className="flex items-center gap-4">
              <Ring value={levelPct} size={84} stroke={8}><div className="text-center"><p className="text-[10px] font-bold uppercase text-muted">Level</p><p className="text-2xl font-extrabold leading-none">{g?.level ?? 1}</p></div></Ring>
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-2xl font-extrabold"><XPGem size={22} /><CountUp value={g?.xp ?? 0} /></p>
                <p className="text-sm text-muted">{g ? `${g.level_ceiling - g.xp} XP to level ${g.level + 1}` : "…"}</p>
              </div>
            </div>
            <div className="mt-5">
              <div className="flex justify-between text-xs font-semibold"><span>Today&apos;s goal</span><span className="text-muted">{g?.today_xp ?? 0}/{g?.daily_goal_xp ?? 30} XP</span></div>
              <Progress value={todayPct} className="mt-1.5 h-2.5" />
            </div>
            <div className="mt-5 flex items-center justify-between">
              <p className="text-sm font-bold">Recent badges</p>
              <Link href="/app/achievements" className="text-xs font-semibold text-brand-700">View all</Link>
            </div>
            <div className="mt-3 flex gap-3">
              {(badges ?? []).filter((b) => b.earned).slice(0, 4).map((b) => (
                <div key={b.slug} title={b.name}><BadgeMedal icon={b.icon} tier={b.tier} earned size={48} /></div>
              ))}
              {badges && !badges.some((b) => b.earned) && <p className="text-sm text-muted">Complete your first quiz to earn <b>First Steps</b>.</p>}
            </div>
          </motion.section>

          <motion.section variants={item} className="card p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-muted">Wallet</p>
              <Link href="/app/wallet#history" className="text-xs font-semibold text-brand-700">History</Link>
            </div>
            <p className="mt-1 flex items-center gap-2 text-3xl font-extrabold"><CreditCoin size={28} /><CountUp value={wallet?.balance ?? me.balance} /></p>
            <p className="text-xs text-muted">credits · 1 credit = ₦10</p>
            <Link href="/app/wallet#buy" className={buttonClass("dark", "md", "mt-4 w-full")}><Plus className="h-4 w-4" /> Buy credits</Link>
          </motion.section>

          <motion.section variants={item} className="card p-5">
            <h2 className="flex items-center gap-2 font-bold"><Lightbulb className="h-5 w-5 text-gold" /> For you</h2>
            <ul className="mt-3 space-y-2">
              {recs.slice(0, 4).map((r) => (
                <li key={r.text}>
                  <Link href={r.href} className="flex items-start gap-3 rounded-xl p-2.5 text-sm transition hover:bg-slate-50">
                    <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                      r.tone === "amber" ? "bg-amber-50 text-amber-600" : r.tone === "red" ? "bg-red-50 text-red-600" : r.tone === "dark" ? "bg-ink text-white" : "bg-brand-50 text-brand-700")}><r.icon className="h-4 w-4" /></span>
                    <span className="pt-1 font-medium">{r.text}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </motion.section>

          <motion.section variants={item} className="grid grid-cols-2 gap-3">
            <Link href="/app/tutor" className="card flex flex-col gap-2 p-4 transition hover:-translate-y-0.5 hover:shadow-lift"><Bot className="h-6 w-6 text-brand-600" /><span className="text-sm font-bold">Ask AI tutor</span></Link>
            <Link href="/app/roadmap" className="card flex flex-col gap-2 p-4 transition hover:-translate-y-0.5 hover:shadow-lift"><Map className="h-6 w-6 text-brand-600" /><span className="text-sm font-bold">My roadmap</span></Link>
          </motion.section>
        </div>
      </div>
    </motion.div>
  );
}

function ContinueCard({ next }: { next: any }) {
  if (!next) return <Skeleton className="h-[150px]" />;
  let href = "/app/learn";
  let cta = "Start learning";
  if (next.source !== "none") {
    if (next.kind === "lesson" && next.lesson_id) { href = `/app/lesson/${next.lesson_id}`; cta = "Continue lesson"; }
    else if (next.kind === "mock") { href = "/app/practice?kind=mock"; cta = "Start mock exam"; }
    else if (next.topic_id) { href = `/app/practice?kind=topic&subject=${next.subject_id}&topic=${next.topic_id}`; cta = "Start practice"; }
    else if (next.subject_id) { href = `/app/practice?subject=${next.subject_id}`; cta = "Start practice"; }
  }
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 p-5 text-white shadow-glow sm:p-6">
      <div className="absolute inset-0 grid-bg-dark opacity-40" />
      <div className="absolute -bottom-16 -right-10 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
      <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15"><BookOpen className="h-7 w-7" /></div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-white/70">{next.source === "roadmap" ? "Next on your roadmap" : next.source === "lesson" ? "Continue where you stopped" : "Recommended"}</p>
          <p className="mt-1 text-xl font-extrabold leading-tight">{next.source === "none" ? "Pick a subject and start your first lesson" : next.title}</p>
          {next.source !== "none" && <p className="mt-1 text-sm text-white/75">{[next.subject, next.minutes && `${next.minutes} min`].filter(Boolean).join(" · ")}</p>}
        </div>
        <Link href={href} className="inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 font-bold text-brand-800 shadow-press transition hover:bg-brand-50 active:translate-y-px">{cta} <ArrowRight className="h-4 w-4" /></Link>
      </div>
    </div>
  );
}
