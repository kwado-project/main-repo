"use client";
import { useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { Check, Copy, Gift, Info, Share2, UserPlus, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, EmptyState, Skeleton } from "@/components/ui/primitives";
import { CreditCoin } from "@/components/ui/fun";
import { fmtDate } from "@/lib/utils";

export default function ReferralsPage() {
  const { data } = useSWR<any>("/referrals");
  const [copied, setCopied] = useState<"code" | "link" | null>(null);
  const copy = (text: string, what: "code" | "link") => { navigator.clipboard.writeText(text); setCopied(what); setTimeout(() => setCopied(null), 1600); };
  if (!data) return <div className="space-y-4"><Skeleton className="h-56" /><Skeleton className="h-32" /></div>;
  const wa = `https://wa.me/?text=${encodeURIComponent(data.share_text)}`;
  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 to-brand-900 p-6 text-white sm:p-8">
        <div className="absolute inset-0 grid-bg-dark opacity-40" />
        <motion.div className="absolute -right-6 -top-6 hidden sm:block" animate={{ rotate: [0, 8, 0] }} transition={{ duration: 5, repeat: Infinity }}><Gift className="h-40 w-40 text-white/10" /></motion.div>
        <div className="relative max-w-xl">
          <Badge tone="dark" className="bg-white/15 ring-white/20">Refer & earn</Badge>
          <h1 className="mt-4 text-3xl font-extrabold leading-tight sm:text-4xl">Earn {data.reward_percent}% back every time a friend buys credits</h1>
          <p className="mt-2 text-white/80">If a friend you invite buys 500 credits, you get 100. It keeps working on every purchase they make.</p>
          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <div className="flex flex-1 items-center justify-between rounded-xl bg-white/10 px-4 py-3 ring-1 ring-white/20">
              <span className="text-xs text-white/60">Your code</span>
              <span className="font-mono text-lg font-bold tracking-widest">{data.code}</span>
              <button onClick={() => copy(data.code, "code")} aria-label="Copy referral code" className="rounded-lg p-1.5 hover:bg-white/10">{copied === "code" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}</button>
            </div>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Button variant="secondary" className="border-0" onClick={() => copy(data.link, "link")}>{copied === "link" ? <><Check className="h-4 w-4" /> Link copied</> : <><Copy className="h-4 w-4" /> Copy referral link</>}</Button>
            <a href={wa} target="_blank" rel="noopener noreferrer" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#25D366] px-5 font-semibold text-white shadow-press hover:brightness-95">
              <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm5.3 14.2c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .1-3.3-.9-2.8-1.2-4.5-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9s.7-2 1-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.4.6-.3.4c-.1.1-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.5.1.6-.1l.9-1.1c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.5.3.1.2.1.7-.1 1.3Z" /></svg>
              Share on WhatsApp
            </a>
          </div>
          {"share" in navigator && <button onClick={() => navigator.share({ text: data.share_text, url: data.link }).catch(() => {})} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-white/80 hover:text-white"><Share2 className="h-4 w-4" /> More sharing options</button>}
        </div>
      </section>

      <section className="grid grid-cols-3 gap-3">
        {[["Total referrals", data.total_referrals, Users], ["Active (bought credits)", data.active_referrals, UserPlus], ["Credits earned", data.total_earned, null]].map(([l, v, I]: any) => (
          <div key={l} className="card p-4 sm:p-5">
            {I ? <I className="h-5 w-5 text-brand-600" /> : <CreditCoin size={20} />}
            <p className="mt-3 text-2xl font-extrabold sm:text-3xl">{v}</p><p className="text-xs text-muted sm:text-sm">{l}</p>
          </div>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5">
          <h2 className="font-bold">Reward activity</h2>
          {data.activity.length === 0 ? <EmptyState icon={Gift} title="No rewards yet" body="When a friend you invited buys credits, your reward shows here." /> : (
            <ul className="mt-3 divide-y divide-line">
              {data.activity.map((a: any, i: number) => (
                <li key={i} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{a.friend} bought {a.purchased} credits</p><p className="text-xs text-muted">{fmtDate(a.date)}</p></div>
                  <Badge tone={a.status === "granted" ? "green" : "gray"}>{a.status === "granted" ? `+${a.reward}` : "Reversed"}</Badge>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card p-5">
          <h2 className="font-bold">Friends you invited</h2>
          {data.referrals.length === 0 ? <EmptyState icon={Users} title="No referrals yet" body="Share your link — friends get 100 free credits when they join." /> : (
            <ul className="mt-3 divide-y divide-line">
              {data.referrals.map((r: any, i: number) => (
                <li key={i} className="flex items-center gap-3 py-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-800">{r.name[0]?.toUpperCase()}</span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{r.name}</p><p className="truncate text-xs text-muted">{r.email} · joined {fmtDate(r.joined_at)}</p></div>
                  {r.active ? <Badge>Active</Badge> : <Badge tone="gray">Joined</Badge>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-line bg-white p-5">
        <h2 className="flex items-center gap-2 font-bold"><Info className="h-5 w-5 text-brand-600" /> How referral rewards work</h2>
        <ul className="mt-3 grid gap-2 text-sm text-muted sm:grid-cols-2">
          <li>• Friends must sign up using your link or code.</li>
          <li>• You earn {data.reward_percent}% of the credits they <b className="text-ink">purchase</b>, every time.</li>
          <li>• Free welcome credits and promotions don&apos;t count.</li>
          <li>• Rewards are reversed if a purchase is refunded or charged back.</li>
          <li>• Referral credits are platform credits — they can&apos;t be withdrawn as cash.</li>
          <li>• Self-referrals and duplicate accounts aren&apos;t eligible.</li>
        </ul>
      </section>
    </div>
  );
}
