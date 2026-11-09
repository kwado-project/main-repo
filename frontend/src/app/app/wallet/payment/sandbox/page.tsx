"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";

/** DEVELOPMENT ONLY — shown when Paystack keys aren't configured. The backend
 *  endpoint behind it is disabled in production. No real money moves here. */
export default function SandboxPage() {
  return <Suspense><Sandbox /></Suspense>;
}

function Sandbox() {
  const ref = useSearchParams().get("reference") ?? "";
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  async function act(outcome: "success" | "failed") {
    setBusy(outcome);
    try {
      await api(`/payments/sandbox/${ref}/complete`, { method: "POST", json: { outcome } });
      router.replace(`/app/wallet/payment/callback?reference=${ref}`);
    } catch (e) { setErr((e as ApiError).message); setBusy(null); }
  }
  return (
    <div className="mx-auto max-w-md pt-10">
      <div className="rounded-3xl border-2 border-dashed border-amber-300 bg-amber-50 p-6">
        <p className="flex items-center gap-2 font-bold text-amber-900"><FlaskConical className="h-5 w-5" /> Development payment sandbox</p>
        <p className="mt-2 text-sm text-amber-900/80">Paystack isn&apos;t configured in this environment, so this page simulates the payment provider. It is disabled in production and no real money moves.</p>
        <p className="mt-4 rounded-xl bg-white p-3 font-mono text-sm">{ref}</p>
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          <Button onClick={() => act("success")} loading={busy === "success"}>Approve payment</Button>
          <Button variant="secondary" onClick={() => act("failed")} loading={busy === "failed"}>Decline payment</Button>
        </div>
        {err && <p className="mt-3 text-sm font-semibold text-red-700">{err}</p>}
      </div>
    </div>
  );
}
