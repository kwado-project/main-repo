"use client";
import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSWRConfig } from "swr";
import { motion } from "framer-motion";
import { Loader2, RefreshCw, XCircle } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { CreditCoin, fireConfetti } from "@/components/ui/fun";
import { api, ApiError } from "@/lib/api";
import { naira } from "@/lib/utils";

export default function CallbackPage() {
  return <Suspense><Callback /></Suspense>;
}

function Callback() {
  const params = useSearchParams();
  const ref = params.get("reference") || params.get("trxref") || "";
  const [state, setState] = useState<"checking" | "success" | "failed" | "pending" | "error">("checking");
  const [p, setP] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const tries = useRef(0);
  const { mutate } = useSWRConfig();

  async function check() {
    setState("checking");
    try {
      const r = await api<any>(`/payments/verify/${ref}`);
      setP(r);
      if (r.status === "success") { setState("success"); fireConfetti({ big: true }); mutate("/wallet"); mutate("/me"); return; }
      if (["failed", "abandoned"].includes(r.status)) { setState("failed"); return; }
      if (tries.current++ < 6) setTimeout(check, 2500);
      else setState("pending");
    } catch (e) {
      const err = e as ApiError;
      if (err.status === 202 && tries.current++ < 6) { setTimeout(check, 2500); return; }
      setMsg(err.message);
      setState("error");
    }
  }

  useEffect(() => { if (ref) check(); else setState("error"); }, [ref]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center text-center">
      {state === "checking" && (
        <>
          <Loader2 className="h-14 w-14 animate-spin text-brand-600" />
          <h1 className="mt-6 text-2xl font-extrabold">Confirming your payment…</h1>
          <p className="mt-2 text-muted">We&apos;re verifying directly with Paystack. This usually takes a few seconds — please don&apos;t close this page.</p>
        </>
      )}
      {state === "success" && p && (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 220, damping: 14 }} className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-brand-600 shadow-glow">
            <svg viewBox="0 0 24 24" className="h-12 w-12 text-white" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round"><motion.path d="M5 12.5l4.5 4.5L19 7.5" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.3 }} /></svg>
          </motion.div>
          <h1 className="mt-6 text-3xl font-extrabold">Payment successful</h1>
          <p className="mt-2 flex items-center justify-center gap-2 text-lg"><CreditCoin size={22} /> <b>{p.credits} credits</b> added to your wallet</p>
          <p className="mt-1 text-sm text-muted">{naira(p.amount_naira)} · {p.reference}</p>
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            <Link href="/app" className={buttonClass("primary", "lg")}>Start learning</Link>
            <Link href={`/app/wallet/receipt/${p.reference}`} className={buttonClass("secondary", "lg")}>View receipt</Link>
          </div>
        </motion.div>
      )}
      {(state === "failed" || state === "error") && (
        <>
          <XCircle className="h-16 w-16 text-red-500" />
          <h1 className="mt-6 text-2xl font-extrabold">Payment {state === "failed" ? "not completed" : "couldn't be confirmed"}</h1>
          <p className="mt-2 text-muted">{state === "failed" ? `${p?.gateway_response || "The payment was declined or cancelled."} You have not been charged credits for this attempt.` : msg || "Something went wrong."}</p>
          {ref && <p className="mt-1 text-xs text-muted">Reference: {ref}</p>}
          <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
            <Link href="/app/wallet#buy" className={buttonClass("primary", "lg")}>Try again</Link>
            <Link href="/app/wallet" className={buttonClass("secondary", "lg")}>Back to wallet</Link>
          </div>
        </>
      )}
      {state === "pending" && (
        <>
          <RefreshCw className="h-14 w-14 text-amber-500" />
          <h1 className="mt-6 text-2xl font-extrabold">Still waiting for your bank</h1>
          <p className="mt-2 text-muted">Some transfers take a few minutes. Your credits will appear automatically once Paystack confirms — no need to pay again.</p>
          <Button size="lg" className="mt-8" onClick={() => { tries.current = 0; check(); }}>Check again</Button>
        </>
      )}
    </div>
  );
}
