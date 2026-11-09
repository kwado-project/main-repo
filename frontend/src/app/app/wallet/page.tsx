"use client";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import useSWRInfinite from "swr/infinite";
import { motion } from "framer-motion";
import { ArrowDownLeft, ArrowUpRight, Gift, Lock, Receipt, ShieldCheck, Sparkles, Wallet as WalletIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, CountUp, EmptyState, Skeleton, Tabs } from "@/components/ui/primitives";
import { Modal } from "@/components/ui/overlay";
import { CreditCoin } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { cn, fmtDate, naira } from "@/lib/utils";

export default function WalletPage() {
  const { data: w } = useSWR<any>("/wallet");
  const { data: packages } = useSWR<any[]>("/wallet/packages");
  const { data: pricing } = useSWR<any[]>("/wallet/pricing");
  const [pick, setPick] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"all" | "purchases" | "earned" | "spent">("all");
  const toast = useToast();

  async function checkout() {
    setBusy(true);
    try {
      const p = await api<any>("/payments/initialize", { method: "POST", json: { package: pick.id } });
      window.location.href = p.authorization_url;
    } catch (e) {
      toast({ tone: "error", title: "Checkout failed", body: (e as ApiError).message });
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold sm:text-3xl">Wallet</h1>
        <p className="mt-1 text-muted">Credits power quizzes, mock exams and the AI tutor. 1 credit = ₦10.</p>
      </div>

      <section className="grid gap-4 lg:grid-cols-[1.3fr_2fr]">
        <div className="relative overflow-hidden rounded-3xl bg-ink p-6 text-white">
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-brand-600/40 blur-3xl" />
          <div className="absolute inset-0 grid-bg-dark opacity-50" />
          <p className="relative flex items-center gap-2 text-sm text-white/60"><WalletIcon className="h-4 w-4" /> Available credits</p>
          <p className="relative mt-2 flex items-center gap-3 text-5xl font-extrabold"><CreditCoin size={44} />{w ? <CountUp value={w.balance} /> : "…"}</p>
          <p className="relative mt-1 text-sm text-white/60">≈ {naira((w?.balance ?? 0) * 10)} of learning</p>
          <a href="#buy" className="relative mt-6 inline-flex h-11 items-center gap-2 rounded-xl bg-brand-600 px-5 font-semibold shadow-press hover:bg-brand-500">Buy credits</a>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[["Purchased", w?.total_purchased, ArrowDownLeft, "text-brand-600"], ["Earned", w?.total_earned, Gift, "text-gold"], ["Spent", w?.total_spent, ArrowUpRight, "text-slate-500"]].map(([l, v, I, c]: any) => (
            <div key={l} className="card flex flex-col justify-between p-4 sm:p-5">
              <I className={cn("h-5 w-5", c)} />
              <div><p className="mt-4 text-2xl font-extrabold sm:text-3xl">{v ?? "–"}</p><p className="text-sm text-muted">{l}</p></div>
            </div>
          ))}
        </div>
      </section>

      <section id="buy" className="scroll-mt-24">
        <h2 className="text-xl font-extrabold">Buy credits</h2>
        <p className="mt-1 text-sm text-muted">Exact credits, no hidden fees. Secure payment by Paystack (cards, bank transfer, USSD).</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {!packages && Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-48" />)}
          {packages?.map((p, i) => (
            <motion.button key={p.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} whileHover={{ y: -4 }} whileTap={{ scale: 0.98 }}
              onClick={() => setPick(p)}
              className={cn("relative flex flex-col rounded-3xl border-2 p-5 text-left transition", p.is_featured ? "border-brand-600 bg-ink text-white shadow-glow" : "border-line bg-white hover:border-brand-300 hover:shadow-lift")}>
              {p.bonus_label && <span className={cn("absolute -top-2.5 left-4 rounded-full px-2.5 py-0.5 text-[11px] font-bold", p.is_featured ? "bg-brand-600 text-white" : "bg-ink text-white")}>{p.bonus_label}</span>}
              <span className={cn("text-sm font-bold", p.is_featured ? "text-brand-400" : "text-brand-700")}>{p.name}</span>
              <span className="mt-3 flex items-center gap-1.5 text-3xl font-extrabold"><CreditCoin size={24} />{p.credits.toLocaleString()}</span>
              <span className={cn("text-xs", p.is_featured ? "text-white/60" : "text-muted")}>credits</span>
              <span className="mt-auto pt-5 text-xl font-extrabold">{naira(p.price_naira)}</span>
              <span className={cn("mt-1 text-xs", p.is_featured ? "text-white/60" : "text-muted")}>{Math.floor(p.credits / 25)} mock exams or {Math.floor(p.credits / 2)} tutor answers</span>
            </motion.button>
          ))}
        </div>
      </section>

      <section id="history" className="scroll-mt-24">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <h2 className="text-xl font-extrabold">Transaction history</h2>
          <Tabs value={tab} onChange={setTab} tabs={[{ value: "all", label: "All" }, { value: "purchases", label: "Purchases" }, { value: "earned", label: "Rewards" }, { value: "spent", label: "Spent" }]} />
        </div>
        {tab === "purchases" ? <Purchases /> : <Transactions kind={tab === "earned" ? "referral_reward" : tab === "spent" ? "spend" : ""} />}
      </section>

      <section className="card p-5">
        <h2 className="font-bold">What things cost</h2>
        <div className="mt-3 grid gap-x-8 sm:grid-cols-2">
          {pricing?.map((p) => <div key={p.key} className="flex justify-between border-b border-dashed border-line py-2.5 text-sm"><span>{p.label}</span><span className="flex items-center gap-1 font-bold"><CreditCoin size={14} />{p.credits}</span></div>)}
        </div>
      </section>

      <Modal open={!!pick} onClose={() => !busy && setPick(null)} title="Confirm your purchase">
        {pick && (
          <div>
            <div className="rounded-2xl bg-canvas p-5">
              <div className="flex items-center justify-between"><span className="font-semibold">{pick.name} package</span><Badge>{pick.credits} credits</Badge></div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted">Credits you receive</span><span className="flex items-center gap-1 font-bold"><CreditCoin size={14} />{pick.credits.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-muted">Price</span><span className="font-bold">{naira(pick.price_naira)}</span></div>
                <div className="flex justify-between border-t border-line pt-2"><span className="font-semibold">Total to pay</span><span className="text-lg font-extrabold">{naira(pick.price_naira)}</span></div>
              </div>
            </div>
            <ul className="mt-4 space-y-2 text-sm text-muted">
              <li className="flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0 text-brand-600" /> You&apos;ll pay on Paystack&apos;s secure page. We never see your card details.</li>
              <li className="flex gap-2"><Lock className="h-4 w-4 shrink-0 text-brand-600" /> Credits are added only after we verify the payment with Paystack.</li>
            </ul>
            <Button size="lg" className="mt-6 w-full" onClick={checkout} loading={busy}>Pay {naira(pick.price_naira)} securely</Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

function Transactions({ kind }: { kind: string }) {
  const getKey = (i: number, prev: any) => {
    if (prev && !prev.next) return null;
    if (i === 0) return `/wallet/transactions${kind ? `?kind=${kind}` : ""}`;
    const u = new URL(prev.next, "http://x");
    return `/wallet/transactions?${u.searchParams.toString()}`;
  };
  const { data, size, setSize, isValidating } = useSWRInfinite<any>(getKey);
  const rows = data?.flatMap((p) => p.results) ?? [];
  const more = data?.[data.length - 1]?.next;
  return (
    <div className="card mt-4 overflow-hidden">
      {!data && <div className="space-y-2 p-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}</div>}
      {data && rows.length === 0 && <EmptyState icon={Receipt} title="No transactions yet" body="Every credit in or out appears here, with a reason." />}
      <ul className="divide-y divide-line">
        {rows.map((t) => (
          <li key={t.id} className="flex items-center gap-3 px-4 py-3.5">
            <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", t.amount > 0 ? "bg-brand-50 text-brand-700" : t.amount < 0 ? "bg-slate-100 text-slate-600" : "bg-slate-50 text-slate-400")}>
              {t.kind === "referral_reward" || t.kind === "signup_bonus" ? <Sparkles className="h-5 w-5" /> : t.amount >= 0 ? <ArrowDownLeft className="h-5 w-5" /> : <ArrowUpRight className="h-5 w-5" />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{t.description}</p>
              <p className="text-xs text-muted">{t.kind_label} · {fmtDate(t.created_at, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</p>
            </div>
            <div className="text-right">
              <p className={cn("font-extrabold tabular-nums", t.amount > 0 ? "text-brand-700" : "text-ink")}>{t.amount > 0 ? "+" : ""}{t.amount}</p>
              <p className="text-[11px] text-muted">bal. {t.balance_after}</p>
            </div>
          </li>
        ))}
      </ul>
      {more && <div className="border-t border-line p-3 text-center"><Button variant="ghost" size="sm" loading={isValidating} onClick={() => setSize(size + 1)}>Load more</Button></div>}
    </div>
  );
}

function Purchases() {
  const { data } = useSWR<any>("/payments");
  const rows = data?.results ?? [];
  return (
    <div className="card mt-4 overflow-hidden">
      {!data && <div className="p-4"><Skeleton className="h-12" /></div>}
      {data && rows.length === 0 && <EmptyState icon={Receipt} title="No purchases yet" body="Your receipts will appear here." />}
      <ul className="divide-y divide-line">
        {rows.map((p: any) => (
          <li key={p.reference} className="flex items-center gap-3 px-4 py-3.5">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{p.package_name} · {p.credits} credits</p>
              <p className="truncate text-xs text-muted">{p.reference} · {fmtDate(p.created_at)}</p>
            </div>
            <Badge tone={p.status === "success" ? "green" : p.status === "pending" ? "amber" : p.status === "refunded" ? "blue" : "red"}>{p.status}</Badge>
            <span className="w-20 text-right font-bold">{naira(p.amount_naira)}</span>
            {p.status === "success" ? <Link href={`/app/wallet/receipt/${p.reference}`} className="text-sm font-semibold text-brand-700">Receipt</Link>
              : p.status === "pending" ? <Link href={`/app/wallet/payment/callback?reference=${p.reference}`} className="text-sm font-semibold text-brand-700">Check</Link> : <span className="w-[52px]" />}
          </li>
        ))}
      </ul>
    </div>
  );
}
