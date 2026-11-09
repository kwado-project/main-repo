"use client";
import useSWR from "swr";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, Banknote, Bot, FileQuestion, Swords, Users } from "lucide-react";
import { Skeleton } from "@/components/ui/primitives";
import { naira } from "@/lib/utils";

function Chart({ title, data, color = "#16A34A", money = false }: { title: string; data?: any[]; color?: string; money?: boolean }) {
  return (
    <div className="card p-5">
      <p className="font-bold">{title}</p>
      <div className="mt-4 h-56">
        {!data ? <Skeleton className="h-full" /> : data.length === 0 ? <p className="flex h-full items-center justify-center text-sm text-muted">No data in the last 30 days</p> : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ left: -16, right: 8, top: 4 }}>
              <defs><linearGradient id={`g${title}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity={0.35} /><stop offset="1" stopColor={color} stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="#E5E7EB" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(d) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" })} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip formatter={(v: any) => (money ? naira(v) : v)} labelFormatter={(d) => new Date(d).toLocaleDateString("en-GB")} contentStyle={{ borderRadius: 12, border: "1px solid #E5E7EB" }} />
              <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} fill={`url(#g${title})`} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

export default function AdminOverview() {
  const { data } = useSWR<any>("/admin-api/overview");
  const t = data?.totals;
  const tiles = [
    ["Students", t?.students, Users], ["Active today", t?.dau, Activity], ["Revenue (30d)", t ? naira(t.revenue_naira_30d) : undefined, Banknote],
    ["Quizzes (30d)", t?.attempts_30d, Swords], ["Published questions", t?.questions_published, FileQuestion], ["Awaiting review", t?.pending_review, FileQuestion],
  ] as const;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold">Analytics</h1>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        {tiles.map(([l, v, I]) => (
          <div key={l} className="card p-4"><I className="h-5 w-5 text-brand-600" /><p className="mt-3 text-2xl font-extrabold">{v ?? "–"}</p><p className="text-xs text-muted">{l}</p></div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Chart title="Sign-ups" data={data?.signups} />
        <Chart title="Verified revenue" data={data?.revenue} color="#111827" money />
        <Chart title="Quizzes submitted" data={data?.attempts} color="#0EA5E9" />
        <div className="card p-5">
          <p className="font-bold">Credits spent by activity (30d)</p>
          <div className="mt-4 h-56">
            {!data ? <Skeleton className="h-full" /> : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.spend_by_activity} layout="vertical" margin={{ left: 40 }}>
                  <XAxis type="number" hide /><YAxis type="category" dataKey="activity" tick={{ fontSize: 11 }} width={120} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 12 }} /><Bar dataKey="credits" fill="#16A34A" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
      <div className="card p-5">
        <p className="flex items-center gap-2 font-bold"><Bot className="h-5 w-5 text-brand-600" /> AI usage (30 days)</p>
        <div className="mt-3 grid grid-cols-2 gap-4 text-sm sm:grid-cols-5">
          {[["Calls", data?.ai?.calls], ["Failed (refunded)", data?.ai?.failed], ["Input tokens", data?.ai?.input], ["Output tokens", data?.ai?.output], ["Cached tokens", data?.ai?.cached]].map(([l, v]) => (
            <div key={l as string}><p className="text-muted">{l}</p><p className="text-lg font-extrabold">{(v as number)?.toLocaleString?.() ?? 0}</p></div>
          ))}
        </div>
      </div>
    </div>
  );
}
