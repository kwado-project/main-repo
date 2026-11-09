"use client";
import Link from "next/link";
import { use } from "react";
import useSWR from "swr";
import { ArrowLeft, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/primitives";
import { LogoMark } from "@/components/ui/logo";
import { fmtDate, naira } from "@/lib/utils";

export default function ReceiptPage({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = use(params);
  const { data: r, error } = useSWR<any>(`/payments/receipt/${ref}`);
  if (error) return <p className="text-center text-muted">Receipt not found.</p>;
  if (!r) return <Skeleton className="mx-auto h-96 max-w-lg" />;
  const rows = [["Reference", r.reference], ["Date", fmtDate(r.verified_at || r.created_at, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })],
    ["Billed to", r.name ? `${r.name} (${r.email})` : r.email], ["Package", r.package_name], ["Credits", r.credits.toLocaleString()],
    ["Payment method", r.channel || "Paystack"], ["Status", r.status === "success" ? "Paid" : r.status]];
  return (
    <div className="mx-auto max-w-lg">
      <div className="mb-4 flex items-center justify-between print:hidden">
        <Link href="/app/wallet" className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" /> Wallet</Link>
        <Button variant="secondary" size="sm" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print / save PDF</Button>
      </div>
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between bg-ink p-6 text-white">
          <div className="flex items-center gap-3"><LogoMark /><div><p className="font-extrabold">Kwado AI</p><p className="text-xs text-white/60">Payment receipt</p></div></div>
          <p className="text-2xl font-extrabold">{naira(r.amount_naira)}</p>
        </div>
        <dl className="divide-y divide-line px-6">
          {rows.map(([k, v]) => <div key={k} className="flex justify-between gap-4 py-3 text-sm"><dt className="text-muted">{k}</dt><dd className="text-right font-semibold">{v}</dd></div>)}
        </dl>
        <p className="border-t border-line bg-canvas px-6 py-4 text-xs text-muted">Credits are non-refundable platform credits and cannot be withdrawn as cash. Keep this reference for support enquiries.</p>
      </div>
    </div>
  );
}
