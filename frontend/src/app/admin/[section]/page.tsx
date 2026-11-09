"use client";
import { use, useState } from "react";
import { notFound } from "next/navigation";
import useSWR from "swr";
import { CheckCircle2, Coins, RefreshCw, Send, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Input, Label, Textarea } from "@/components/ui/primitives";
import { ConfirmDialog, Modal } from "@/components/ui/overlay";
import { useToast } from "@/components/ui/toast";
import { ResourceTable, StatusBadge, type Column, type Field } from "@/components/admin/resource";
import { QuestionBank } from "@/components/admin/questions";
import { api, ApiError } from "@/lib/api";
import { fmtDate, naira, uid } from "@/lib/utils";

const date = (k: string): Column => ({ key: k, label: "Date", render: (r) => <span className="whitespace-nowrap text-muted">{r[k] ? fmtDate(r[k], { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}</span> });
const status = (k = "status", label = "Status"): Column => ({ key: k, label, render: (r) => <StatusBadge value={String(r[k])} /> });
const color = (k = "color"): Column => ({ key: k, label: "", render: (r) => <span className="inline-block h-5 w-5 rounded-md" style={{ background: r[k] }} /> });

export default function AdminSection({ params }: { params: Promise<{ section: string }> }) {
  const { section } = use(params);
  switch (section) {
    case "questions": return <QuestionBank />;
    case "examinations":
      return <ResourceTable title="Examinations" endpoint="/admin-api/examinations" description="Examination types and subject-count rules."
        columns={[color(), { key: "name", label: "Name" }, { key: "code", label: "Code" }, { key: "min_subjects", label: "Min" }, { key: "max_subjects", label: "Max" }, { key: "mock_duration_minutes", label: "Mock (min)" }, { key: "is_active", label: "Active" }]}
        fields={[{ name: "name", label: "Name", required: true }, { name: "code", label: "Code (slug)", required: true }, { name: "full_name", label: "Full name", full: true },
          { name: "description", label: "Description", type: "textarea" }, { name: "min_subjects", label: "Minimum subjects", type: "number" }, { name: "max_subjects", label: "Maximum subjects", type: "number" },
          { name: "questions_per_subject_mock", label: "Questions per subject (mock)", type: "number" }, { name: "mock_duration_minutes", label: "Mock duration (minutes)", type: "number" },
          { name: "rules_note", label: "Rules note shown to students", full: true }, { name: "color", label: "Colour", type: "color" }, { name: "order", label: "Order", type: "number" }, { name: "is_active", label: "Active", type: "bool" }]} />;
    case "exam-subjects":
      return <ResourceTable title="Exam rules" endpoint="/admin-api/exam-subjects" searchable={false} description="Which subjects each examination offers, and which are compulsory."
        filters={[]} columns={[{ key: "examination", label: "Examination ID" }, { key: "subject", label: "Subject ID" }, { key: "is_compulsory", label: "Compulsory" }]}
        fields={[{ name: "examination", label: "Examination", type: "select", optionsFrom: "/admin-api/examinations" }, { name: "subject", label: "Subject", type: "select", optionsFrom: "/admin-api/subjects" }, { name: "is_compulsory", label: "Compulsory", type: "bool" }]} />;
    case "subjects":
      return <ResourceTable title="Subjects" endpoint="/admin-api/subjects"
        columns={[color(), { key: "name", label: "Name" }, { key: "slug", label: "Slug" }, { key: "icon", label: "Icon" }, { key: "is_active", label: "Active" }]}
        fields={[{ name: "name", label: "Name", required: true }, { name: "slug", label: "Slug", required: true }, { name: "icon", label: "Icon", help: "Lucide icon name, e.g. sigma, leaf, atom" }, { name: "color", label: "Colour", type: "color" },
          { name: "description", label: "Description", type: "textarea" }, { name: "is_active", label: "Active", type: "bool" }]} />;
    case "topics":
      return <ResourceTable title="Topics" endpoint="/admin-api/topics" defaults={{ weight: 2, is_active: true }}
        columns={[{ key: "name", label: "Name" }, { key: "subject", label: "Subject ID" }, { key: "parent", label: "Parent" }, { key: "order", label: "Order" }, { key: "weight", label: "Weight" }, { key: "is_active", label: "Active" }]}
        fields={[{ name: "subject", label: "Subject", type: "select", optionsFrom: "/admin-api/subjects", required: true }, { name: "parent", label: "Parent topic (for subtopics)", type: "select", optionsFrom: "/admin-api/topics" },
          { name: "name", label: "Name", required: true }, { name: "slug", label: "Slug", required: true }, { name: "order", label: "Order", type: "number" },
          { name: "weight", label: "Exam weight (1–5)", type: "number" }, { name: "description", label: "Description", type: "textarea" }, { name: "is_active", label: "Active", type: "bool" }]} />;
    case "lessons":
      return <ResourceTable title="Lessons" endpoint="/admin-api/lessons" filters={[{ name: "is_published", label: "Published", options: [{ value: "true", label: "Yes" }, { value: "false", label: "No" }] }]} defaults={{ content: [], estimated_minutes: 8, xp_reward: 20 }}
        columns={[{ key: "title", label: "Title" }, { key: "topic", label: "Topic ID" }, { key: "estimated_minutes", label: "Min" }, { key: "xp_reward", label: "XP" }, { key: "is_published", label: "Published" }]}
        fields={[{ name: "topic", label: "Topic", type: "select", optionsFrom: "/admin-api/topics", required: true }, { name: "title", label: "Title", required: true }, { name: "slug", label: "Slug", required: true },
          { name: "objective", label: "Objective", full: true }, { name: "estimated_minutes", label: "Estimated minutes", type: "number" }, { name: "xp_reward", label: "XP reward", type: "number" }, { name: "order", label: "Order", type: "number" },
          { name: "is_published", label: "Published", type: "bool" },
          { name: "content", label: "Content blocks (JSON)", type: "json", help: 'Blocks: {"type":"text","title","body"} · {"type":"formula","body"} · {"type":"example","title","steps":[]} · {"type":"tip","body"} · {"type":"table","rows":[[a,b]]} · {"type":"check","question","options":[],"answer":0,"explanation"}' }]} />;
    case "learning-paths":
      return <div className="space-y-10">
        <ResourceTable title="Learning paths" endpoint="/admin-api/learning-paths" searchable={false}
          columns={[{ key: "title", label: "Title" }, { key: "subject", label: "Subject ID" }, { key: "examination", label: "Exam ID" }, { key: "is_published", label: "Published" }]}
          fields={[{ name: "title", label: "Title" }, { name: "subject", label: "Subject", type: "select", optionsFrom: "/admin-api/subjects" }, { name: "examination", label: "Examination (blank = all)", type: "select", optionsFrom: "/admin-api/examinations" }, { name: "is_published", label: "Published", type: "bool" }]} />
        <ResourceTable title="Path nodes" endpoint="/admin-api/learning-path-nodes" searchable={false}
          columns={[{ key: "path", label: "Path" }, { key: "order", label: "Order" }, { key: "kind", label: "Kind" }, { key: "title", label: "Title" }, { key: "pass_mark", label: "Pass %" }]}
          fields={[{ name: "path", label: "Path", type: "select", optionsFrom: "/admin-api/learning-paths", optionLabel: "title" }, { name: "order", label: "Order", type: "number" },
            { name: "kind", label: "Kind", type: "select", options: [{ value: "lesson", label: "Lesson" }, { value: "challenge", label: "Topic challenge" }, { value: "boss", label: "Boss challenge" }] },
            { name: "title", label: "Title" }, { name: "lesson", label: "Lesson", type: "select", optionsFrom: "/admin-api/lessons", optionLabel: "title" }, { name: "topic", label: "Topic", type: "select", optionsFrom: "/admin-api/topics" }, { name: "pass_mark", label: "Pass mark %", type: "number" }]} />
      </div>;
    case "users": return <Users />;
    case "payments":
      return <ResourceTable title="Payments" endpoint="/admin-api/payments" canCreate={false} canDelete={false}
        filters={[{ name: "status", label: "Status", options: ["pending", "success", "failed", "abandoned", "refunded"].map((v) => ({ value: v, label: v })) }]}
        columns={[{ key: "reference", label: "Reference", render: (r) => <span className="font-mono text-xs">{r.reference}</span> }, { key: "user_email", label: "Student" }, { key: "package_name", label: "Package" },
          { key: "amount_kobo", label: "Amount", render: (r) => naira(r.amount_kobo / 100) }, { key: "credits", label: "Credits" }, { key: "provider", label: "Provider" }, status(), date("created_at")]}
        rowActions={(r, reload) => <PaymentActions row={r} reload={reload} />} />;
    case "transactions":
      return <ResourceTable title="Wallet ledger" endpoint="/admin-api/transactions" canCreate={false} canDelete={false} description="Append-only. Every credit movement on the platform."
        filters={[{ name: "kind", label: "Type", options: ["purchase", "signup_bonus", "referral_reward", "spend", "refund", "reversal", "adjustment"].map((v) => ({ value: v, label: v })) }]}
        columns={[{ key: "user_email", label: "Student" }, { key: "kind", label: "Type", render: (r) => <StatusBadge value={r.kind} /> }, { key: "amount", label: "Amount", render: (r) => <b className={r.amount > 0 ? "text-brand-700" : ""}>{r.amount > 0 ? "+" : ""}{r.amount}</b> },
          { key: "balance_after", label: "Balance" }, { key: "description", label: "Description" }, date("created_at")]} />;
    case "referral-rewards":
      return <ResourceTable title="Referral rewards" endpoint="/admin-api/referral-rewards" canCreate={false} canDelete={false}
        filters={[{ name: "status", label: "Status", options: [{ value: "granted", label: "Granted" }, { value: "reversed", label: "Reversed" }] }]}
        columns={[{ key: "referrer", label: "Referrer" }, { key: "referred", label: "Referred" }, { key: "reference", label: "Payment" }, { key: "purchased_credits", label: "Purchased" }, { key: "reward_credits", label: "Reward" }, status(), date("created_at")]} />;
    case "packages":
      return <ResourceTable title="Credit packages" endpoint="/admin-api/packages" description="Prices in kobo (₦1 = 100 kobo). Changes apply to new checkouts immediately."
        columns={[{ key: "name", label: "Name" }, { key: "credits", label: "Credits" }, { key: "price_kobo", label: "Price", render: (r) => naira(r.price_kobo / 100) }, { key: "bonus_label", label: "Label" }, { key: "is_featured", label: "Featured" }, { key: "is_active", label: "Active" }]}
        fields={[{ name: "name", label: "Name", required: true }, { name: "slug", label: "Slug", required: true }, { name: "credits", label: "Credits", type: "number" }, { name: "price_kobo", label: "Price (kobo)", type: "number", help: "e.g. 500000 = ₦5,000" },
          { name: "bonus_label", label: "Label" }, { name: "order", label: "Order", type: "number" }, { name: "is_featured", label: "Featured", type: "bool" }, { name: "is_active", label: "Active", type: "bool" }]} />;
    case "pricing":
      return <ResourceTable title="Activity pricing" endpoint="/admin-api/pricing" description="Credit cost of each paid activity. Students always see the cost before confirming."
        columns={[{ key: "key", label: "Key", render: (r) => <span className="font-mono text-xs">{r.key}</span> }, { key: "label", label: "Activity" }, { key: "credits", label: "Credits", render: (r) => <b>{r.credits}</b> }, { key: "is_active", label: "Active" }]}
        fields={[{ name: "key", label: "Key", required: true, help: "e.g. daily_practice, ai_tutor_response" }, { name: "label", label: "Label" }, { name: "credits", label: "Credits", type: "number" }, { name: "description", label: "Description", full: true }, { name: "is_active", label: "Active", type: "bool" }]} />;
    case "ai-config":
      return <ResourceTable title="AI configuration" endpoint="/admin-api/ai-config" searchable={false} description="Per-purpose model routing, effort and token limits. Leave blank to use the defaults."
        columns={[{ key: "purpose", label: "Purpose" }, { key: "model", label: "Model", render: (r) => r.model || <span className="text-muted">default</span> }, { key: "effort", label: "Effort", render: (r) => r.effort || <span className="text-muted">default</span> },
          { key: "max_tokens", label: "Max tokens" }, { key: "daily_user_limit", label: "Daily limit / student" }, { key: "is_enabled", label: "Enabled" }]}
        fields={[{ name: "purpose", label: "Purpose" }, { name: "model", label: "Model ID", help: "e.g. claude-opus-5-5" },
          { name: "effort", label: "Effort", type: "select", options: ["low", "medium", "high", "xhigh", "max"].map((v) => ({ value: v, label: v })) },
          { name: "max_tokens", label: "Max output tokens", type: "number" }, { name: "daily_user_limit", label: "Daily calls per student", type: "number" }, { name: "is_enabled", label: "Enabled", type: "bool" }]} />;
    case "materials":
      return <ResourceTable title="Uploaded materials" endpoint="/admin-api/materials" canCreate={false} canDelete={false} searchable={false} description="Metadata only — student documents stay private."
        filters={[{ name: "status", label: "Status", options: ["uploaded", "processing", "ready", "failed"].map((v) => ({ value: v, label: v })) }]}
        columns={[{ key: "title", label: "Title" }, { key: "owner", label: "Owner ID" }, { key: "visibility", label: "Visibility" }, { key: "content_type", label: "Type" }, { key: "size_bytes", label: "Size", render: (r) => `${(r.size_bytes / 1048576).toFixed(1)} MB` }, status(), date("created_at")]} />;
    case "audit-logs":
      return <ResourceTable title="Audit log" endpoint="/admin-api/audit-logs" canCreate={false} canDelete={false} canEdit={false}
        columns={[date("created_at"), { key: "action", label: "Action", render: (r) => <span className="font-mono text-xs">{r.action}</span> }, { key: "actor", label: "Actor" }, { key: "target_type", label: "Target" }, { key: "target_id", label: "ID" }, { key: "ip_address", label: "IP" }]} />;
    case "settings":
      return <ResourceTable title="System settings" endpoint="/admin-api/settings" searchable={false}
        columns={[{ key: "key", label: "Key" }, { key: "description", label: "Description" }, { key: "value", label: "Value", render: (r) => <code className="text-xs">{JSON.stringify(r.value).slice(0, 60)}</code> }]}
        fields={[{ name: "key", label: "Key" }, { name: "description", label: "Description" }, { name: "value", label: "Value (JSON)", type: "json" }]} />;
    case "broadcast": return <Broadcast />;
    default: notFound();
  }
}

function PaymentActions({ row, reload }: { row: any; reload: () => void }) {
  const [c, setC] = useState<"refund" | null>(null);
  const toast = useToast();
  return (
    <>
      {row.status === "pending" && row.provider === "paystack" && <Button size="sm" variant="ghost" onClick={async () => { await api(`/admin-api/payments/${row.id}/reverify`, { method: "POST" }); toast({ tone: "info", title: "Re-verified with Paystack" }); reload(); }}><RefreshCw className="h-4 w-4" /> Verify</Button>}
      {row.status === "success" && <Button size="sm" variant="ghost" onClick={() => setC("refund")}><Undo2 className="h-4 w-4" /> Refund</Button>}
      <ConfirmDialog open={c === "refund"} onClose={() => setC(null)} danger title="Record a refund?" confirmLabel="Reverse credits"
        body="Purchased credits (and any referral reward) will be reversed. Issue the money refund in the Paystack dashboard."
        onConfirm={async () => { await api(`/admin-api/payments/${row.id}/refund`, { method: "POST" }); setC(null); reload(); }} />
    </>
  );
}

function Users() {
  const [adj, setAdj] = useState<any>(null);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  return (
    <>
      <ResourceTable title="Students & users" endpoint="/admin-api/users" canCreate={false} canDelete={false}
        filters={[{ name: "role", label: "Role", options: [{ value: "student", label: "Student" }, { value: "content_manager", label: "Content manager" }, { value: "admin", label: "Admin" }] },
          { name: "is_active", label: "Status", options: [{ value: "true", label: "Active" }, { value: "false", label: "Suspended" }] }]}
        columns={[{ key: "email", label: "Email" }, { key: "full_name", label: "Name" }, { key: "role", label: "Role", render: (r) => <Badge tone={r.role === "admin" ? "dark" : r.role === "content_manager" ? "blue" : "gray"}>{r.role}</Badge> },
          { key: "balance", label: "Credits" }, { key: "xp", label: "XP" }, { key: "is_active", label: "Active" }, date("date_joined")]}
        fields={[{ name: "full_name", label: "Full name" }, { name: "role", label: "Role", type: "select", options: [{ value: "student", label: "Student" }, { value: "content_manager", label: "Content manager" }, { value: "admin", label: "Administrator" }] }, { name: "is_active", label: "Active (uncheck to suspend)", type: "bool" }]}
        rowActions={(r) => <Button size="sm" variant="ghost" onClick={() => { setAdj(r); setAmount(""); setReason(""); }}><Coins className="h-4 w-4" /> Credits</Button>} />
      <Modal open={!!adj} onClose={() => setAdj(null)} title="Adjust credits" description={adj?.email}>
        <Label>Amount (negative to deduct)</Label><Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <Label className="mt-4">Reason (shown in the student&apos;s history)</Label><Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} />
        <Button className="mt-5 w-full" loading={busy} disabled={!Number(amount) || !reason.trim()} onClick={async () => {
          setBusy(true);
          try { await api(`/admin-api/users/${adj.id}/adjust_credits`, { method: "POST", json: { amount: Number(amount), reason, idempotency_key: uid() } }); toast({ tone: "success", title: "Credits adjusted" }); setAdj(null); }
          catch (e) { toast({ tone: "error", title: "Failed", body: (e as ApiError).message }); } finally { setBusy(false); }
        }}>Apply adjustment</Button>
      </Modal>
    </>
  );
}

function Broadcast() {
  const [title, setTitle] = useState(""), [body, setBody] = useState(""), [link, setLink] = useState("");
  const [confirm, setConfirm] = useState(false), [busy, setBusy] = useState(false);
  const toast = useToast();
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-extrabold">Notifications</h1>
      <p className="mt-1 text-sm text-muted">Send an in-app notification to every active student.</p>
      <div className="card mt-5 space-y-4 p-5">
        <div><Label>Title</Label><Input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} /></div>
        <div><Label>Message</Label><Textarea value={body} maxLength={255} rows={3} onChange={(e) => setBody(e.target.value)} /></div>
        <div><Label>Link (optional)</Label><Input value={link} placeholder="/app/practice" onChange={(e) => setLink(e.target.value)} /></div>
        <Button disabled={!title} onClick={() => setConfirm(true)}><Send className="h-4 w-4" /> Send to all students</Button>
      </div>
      <ConfirmDialog open={confirm} onClose={() => setConfirm(false)} loading={busy} title="Send to every student?" confirmLabel="Send"
        onConfirm={async () => { setBusy(true); try { const r = await api<any>("/admin-api/broadcast", { method: "POST", json: { title, body, link } }); toast({ tone: "success", title: `Sent to ${r.sent} students` }); setTitle(""); setBody(""); setLink(""); } finally { setBusy(false); setConfirm(false); } }} />
      <p className="mt-4 flex items-center gap-1.5 text-xs text-muted"><CheckCircle2 className="h-4 w-4" /> Broadcasts are recorded in the audit log.</p>
    </div>
  );
}
