"use client";
import Link from "next/link";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { motion } from "framer-motion";
import { BrainCircuit, CalendarCheck, ChevronRight, Crown, FileCheck2, Heart, History as HistoryIcon, ListChecks, PlayCircle, Swords, Timer } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { Badge, EmptyState, Select, Skeleton, Tabs } from "@/components/ui/primitives";
import { ConfirmDialog } from "@/components/ui/overlay";
import { CreditCoin } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Pricing } from "@/lib/types";
import { cn, fmtDate, uid } from "@/lib/utils";

const KINDS = [
  { kind: "daily", title: "Daily practice", desc: "10 questions, weighted to your weak topics", icon: CalendarCheck, pricing: "daily_practice", needs: "subject" },
  { kind: "topic", title: "Topic quiz", desc: "20 questions on one topic", icon: ListChecks, pricing: "topic_quiz", needs: "topic" },
  { kind: "subject", title: "Subject assessment", desc: "40 questions · timed · exam mode", icon: FileCheck2, pricing: "subject_assessment", needs: "subject" },
  { kind: "mock", title: "Full mock exam", desc: "All your subjects, real exam timing", icon: Crown, pricing: "mock_exam", needs: "none" },
  { kind: "diagnostic", title: "Diagnostic", desc: "Find your strengths and gaps", icon: BrainCircuit, pricing: "diagnostic", needs: "none" },
  { kind: "challenge", title: "Hearts challenge", desc: "10 questions, 3 lives. Free!", icon: Heart, pricing: null, needs: "topic" },
] as const;

export default function PracticePage() {
  return <Suspense><Practice /></Suspense>;
}

function Practice() {
  const { me } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const toast = useToast();
  const { data: pricing } = useSWR<Pricing[]>("/wallet/pricing");
  const { data: wallet, mutate: mutateWallet } = useSWR<any>("/wallet");
  const { data: progress } = useSWR<any[]>("/assessments/progress");
  const [kind, setKind] = useState<string>(params.get("kind") ?? "daily");
  const [subject, setSubject] = useState<string>(params.get("subject") ?? "");
  const [topic, setTopic] = useState<string>(params.get("topic") ?? "");
  const [mode, setMode] = useState<"practice" | "exam">("practice");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const key = useRef(uid());
  const { data: topics } = useSWR<any[]>(subject ? `/assessments/subjects/${subject}/topics` : null);

  const cfg = KINDS.find((k) => k.kind === kind)!;
  const cost = cfg.pricing ? pricing?.find((p) => p.key === cfg.pricing)?.credits ?? 0 : 0;
  const balance = wallet?.balance ?? me?.balance ?? 0;
  const subjects = useMemo(() => progress?.map((p) => p.subject) ?? [], [progress]);
  useEffect(() => { if (!subject && subjects.length) setSubject(String(subjects[0].id)); }, [subjects, subject]);

  const ready = cfg.needs === "none" || (cfg.needs === "subject" && subject) || (cfg.needs === "topic" && subject && topic);
  const examMode = kind === "mock" || kind === "diagnostic" || kind === "subject";

  async function start() {
    setBusy(true);
    try {
      const a = await api<{ id: number }>("/assessments/attempts", {
        method: "POST",
        json: { kind, subject: cfg.needs !== "none" ? Number(subject) : null, topic: cfg.needs === "topic" ? Number(topic) : null,
                mode: examMode ? undefined : mode, idempotency_key: key.current },
      });
      mutateWallet();
      router.push(`/app/quiz/${a.id}`);
    } catch (e) {
      const err = e as ApiError;
      setConfirm(false);
      if (err.status === 402) toast({ tone: "error", title: "Not enough credits", body: "Top up your wallet to continue." });
      else toast({ tone: "error", title: "Couldn't start", body: err.message });
      key.current = uid();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (params.get("auto") === "1" && kind === "challenge" && subject && topic) start();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <h1 className="text-2xl font-extrabold sm:text-3xl">Practice</h1>
      <p className="mt-1 text-muted">Pick a format. You&apos;ll always see the cost before you start.</p>

      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-3">
        {KINDS.map((k) => {
          const c = k.pricing ? pricing?.find((p) => p.key === k.pricing)?.credits : 0;
          const sel = kind === k.kind;
          return (
            <motion.button key={k.kind} whileTap={{ scale: 0.98 }} onClick={() => setKind(k.kind)}
              className={cn("relative flex flex-col items-start rounded-2xl border-2 bg-white p-4 text-left transition", sel ? "border-brand-600 shadow-glow" : "border-line hover:border-brand-300")}>
              <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", sel ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700")}><k.icon className="h-5 w-5" /></span>
              <span className="mt-3 font-bold">{k.title}</span>
              <span className="mt-0.5 text-xs text-muted sm:text-sm">{k.desc}</span>
              <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold">{c ? <><CreditCoin size={14} /> {c} credits</> : <span className="text-brand-700">Free</span>}</span>
            </motion.button>
          );
        })}
      </div>

      <div className="card mt-5 p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          {cfg.needs !== "none" && (
            <div>
              <label className="mb-1.5 block text-sm font-semibold" htmlFor="subject">Subject</label>
              <Select id="subject" value={subject} onChange={(e) => { setSubject(e.target.value); setTopic(""); }}>
                {!subjects.length && <option value="">Loading…</option>}
                {subjects.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </div>
          )}
          {cfg.needs === "topic" && (
            <div>
              <label className="mb-1.5 block text-sm font-semibold" htmlFor="topic">Topic</label>
              <Select id="topic" value={topic} onChange={(e) => setTopic(e.target.value)}>
                <option value="">Choose a topic</option>
                {topics?.map((t) => <option key={t.id} value={t.id}>{t.name}{t.mastery !== null ? ` · ${t.mastery}%` : ""}</option>)}
              </Select>
            </div>
          )}
          {!examMode && kind !== "challenge" && (
            <div className="sm:col-span-2">
              <p className="mb-1.5 text-sm font-semibold">Mode</p>
              <Tabs value={mode} onChange={setMode} tabs={[{ value: "practice", label: "Practice — instant feedback" }, { value: "exam", label: "Exam — feedback at the end" }]} />
            </div>
          )}
          {examMode && <p className="flex items-center gap-2 text-sm text-muted sm:col-span-2"><Timer className="h-4 w-4 text-brand-600" /> Timed exam simulation — corrections are shown after you submit.</p>}
        </div>
        <div className="mt-5 flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted">Cost: <b className="text-ink">{cost ? `${cost} credits` : "Free"}</b> · Balance: <b className="text-ink">{balance} credits</b></p>
          {cost > balance ? (
            <Link href="/app/wallet#buy" className={buttonClass("dark", "lg")}>Top up to continue</Link>
          ) : (
            <Button size="lg" disabled={!ready} onClick={() => (cost ? setConfirm(true) : start())} loading={busy && !confirm}><Swords className="h-5 w-5" /> Start {cfg.title.toLowerCase()}</Button>
          )}
        </div>
      </div>

      <History />

      <ConfirmDialog open={confirm} onClose={() => setConfirm(false)} onConfirm={start} loading={busy} title={`Start ${cfg.title.toLowerCase()}?`} confirmLabel={`Use ${cost} credits`}
        body={<>This will use <b className="text-ink">{cost} credits</b> from your balance of {balance}. If we can&apos;t build the quiz, you won&apos;t be charged.</>} />
    </div>
  );
}

function History() {
  const { data } = useSWR<any>("/assessments/attempts?page_size=10");
  const { data: open } = useSWR<any>("/assessments/attempts?status=in_progress&page_size=5");
  return (
    <section className="mt-8">
      {open?.results?.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-bold">Unfinished</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {open.results.map((a: any) => (
              <Link key={a.id} href={`/app/quiz/${a.id}`} className="card flex items-center gap-3 p-4 transition hover:shadow-lift">
                <PlayCircle className="h-8 w-8 text-brand-600" />
                <div className="min-w-0 flex-1"><p className="truncate font-semibold">{a.kind_label}{a.subject_name ? ` · ${a.subject_name}` : ""}</p><p className="text-xs text-muted">{a.total_questions} questions · started {fmtDate(a.started_at)}</p></div>
                <span className="text-sm font-bold text-brand-700">Resume</span>
              </Link>
            ))}
          </div>
        </div>
      )}
      <h2 className="flex items-center gap-2 text-lg font-bold"><HistoryIcon className="h-5 w-5 text-muted" /> Recent results</h2>
      <div className="card mt-3 divide-y divide-line">
        {!data && <div className="space-y-2 p-4">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12" />)}</div>}
        {data?.results?.length === 0 && <EmptyState icon={Swords} title="No quizzes yet" body="Your results will appear here." />}
        {data?.results?.map((a: any) => (
          <Link key={a.id} href={`/app/quiz/${a.id}`} className="flex items-center gap-4 p-4 hover:bg-slate-50">
            <span className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-sm font-extrabold", Number(a.score_percent) >= 70 ? "bg-brand-50 text-brand-700" : Number(a.score_percent) >= 50 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-600")}>
              {Math.round(Number(a.score_percent))}%
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold">{a.kind_label}{a.subject_name ? ` · ${a.subject_name}` : ""}{a.topic_name ? ` · ${a.topic_name}` : ""}</p>
              <p className="text-xs text-muted">{a.correct_count}/{a.total_questions} correct · {fmtDate(a.submitted_at)}</p>
            </div>
            <Badge tone="green">+{a.xp_earned} XP</Badge>
            <ChevronRight className="hidden h-4 w-4 text-slate-300 sm:block" />
          </Link>
        ))}
      </div>
    </section>
  );
}
