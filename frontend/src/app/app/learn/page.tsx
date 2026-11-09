"use client";
import Link from "next/link";
import useSWR from "swr";
import { motion } from "framer-motion";
import { ChevronRight, BookOpen } from "lucide-react";
import { EmptyState, Progress, Skeleton } from "@/components/ui/primitives";
import { DynIcon } from "@/components/ui/fun";
import { buttonClass } from "@/components/ui/button";

export default function LearnPage() {
  const { data } = useSWR<any[]>("/assessments/progress");
  return (
    <div>
      <h1 className="text-2xl font-extrabold sm:text-3xl">Learn</h1>
      <p className="mt-1 text-muted">Choose a subject to continue your learning journey.</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {!data && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-44" />)}
        {data?.length === 0 && (
          <div className="card sm:col-span-2 xl:col-span-3">
            <EmptyState icon={BookOpen} title="No subjects yet" body="Finish setting up your examination to see your subjects here."
              action={<Link href="/onboarding" className={buttonClass()}>Set up my exam</Link>} />
          </div>
        )}
        {data?.map((p, i) => (
          <motion.div key={p.subject.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Link href={`/app/learn/${p.subject.id}`} className="group card relative block overflow-hidden p-5 transition hover:-translate-y-1 hover:shadow-lift">
              <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full opacity-10 transition group-hover:scale-125" style={{ background: p.subject.color }} />
              <span className="relative flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-card" style={{ background: p.subject.color }}><DynIcon name={p.subject.icon} className="h-6 w-6" /></span>
              <h2 className="relative mt-4 text-lg font-bold">{p.subject.name}</h2>
              <p className="relative text-sm text-muted">{p.topics_practised} of {p.topics_total} topics practised · {p.level}</p>
              <div className="relative mt-4 flex items-center gap-3"><Progress value={p.mastery} /><span className="text-sm font-bold">{p.mastery}%</span></div>
              <ChevronRight className="absolute right-4 top-5 h-5 w-5 text-slate-300 transition group-hover:translate-x-1 group-hover:text-brand-600" />
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
