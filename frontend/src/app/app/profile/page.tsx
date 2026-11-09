"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { Bell, Check, Gift, GraduationCap, Lock, LogOut, Plus, ShieldCheck, Trash2, User } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { Avatar, Badge, Input, Label, Select, Switch } from "@/components/ui/primitives";
import { ConfirmDialog, Modal } from "@/components/ui/overlay";
import { DynIcon } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Examination, StudentExam } from "@/lib/types";
import { cn, fmtDate } from "@/lib/utils";

const COLORS = ["#16A34A", "#15803D", "#0EA5E9", "#8B5CF6", "#F59E0B", "#EF4444", "#EC4899", "#111827"];

export default function ProfilePage() {
  const { me, reload, signOut } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [form, setForm] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<StudentExam | null>(null);
  const [archive, setArchive] = useState<StudentExam | null>(null);

  useEffect(() => {
    if (me && !form) setForm({ full_name: me.full_name, ...me.profile });
  }, [me, form]);
  if (!me || !form) return null;

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));
  async function save(patch?: any) {
    setSaving(true);
    try {
      const { full_name, ...profile } = patch ?? form;
      await api("/me", { method: "PATCH", json: { full_name, profile: { display_name: profile.display_name, avatar_color: profile.avatar_color, state: profile.state, school: profile.school, study_goal: profile.study_goal, daily_goal_minutes: profile.daily_goal_minutes, leaderboard_visibility: profile.leaderboard_visibility, notify_email_reminders: profile.notify_email_reminders, notify_streak: profile.notify_streak, notify_product: profile.notify_product } } });
      await reload();
      toast({ tone: "success", title: "Saved" });
    } catch (e) {
      toast({ tone: "error", title: "Couldn't save", body: (e as ApiError).message });
    } finally { setSaving(false); }
  }
  const toggle = (k: string) => (v: boolean) => { const next = { ...form, [k]: v }; setForm(next); save(next); };
  const exams = me.student_exams;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-extrabold sm:text-3xl">Profile & settings</h1>

      <Section icon={User} title="Profile">
        <div className="flex items-center gap-4">
          <Avatar name={form.display_name || form.full_name || me.email} color={form.avatar_color} size={64} />
          <div>
            <p className="text-sm font-semibold">Profile colour</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {COLORS.map((c) => <button key={c} onClick={() => set("avatar_color", c)} aria-label={`Colour ${c}`} className={cn("h-8 w-8 rounded-full ring-2 ring-offset-2 transition", form.avatar_color === c ? "ring-ink" : "ring-transparent")} style={{ background: c }} />)}
            </div>
          </div>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div><Label htmlFor="fn">Full name</Label><Input id="fn" value={form.full_name ?? ""} onChange={(e) => set("full_name", e.target.value)} /></div>
          <div><Label htmlFor="dn">Display name</Label><Input id="dn" value={form.display_name ?? ""} maxLength={40} placeholder="Shown on leaderboards" onChange={(e) => set("display_name", e.target.value)} /></div>
          <div><Label htmlFor="em">Email address</Label><Input id="em" value={me.email} disabled className="bg-slate-50" /><p className="mt-1 text-xs text-muted">Your sign-in email. Contact support to change it.</p></div>
          <div><Label htmlFor="st">State</Label><Input id="st" value={form.state ?? ""} placeholder="e.g. Lagos" onChange={(e) => set("state", e.target.value)} /></div>
          <div className="sm:col-span-2"><Label htmlFor="sc">School</Label><Input id="sc" value={form.school ?? ""} onChange={(e) => set("school", e.target.value)} /></div>
          <div className="sm:col-span-2"><Label htmlFor="sg">Study goal</Label><Input id="sg" value={form.study_goal ?? ""} placeholder="e.g. Score 300+ in JAMB and study Medicine at UNILAG" onChange={(e) => set("study_goal", e.target.value)} /></div>
          <div><Label htmlFor="dg">Daily goal</Label>
            <Select id="dg" value={form.daily_goal_minutes} onChange={(e) => set("daily_goal_minutes", Number(e.target.value))}>{[15, 30, 45, 60, 90, 120].map((m) => <option key={m} value={m}>{m} minutes a day</option>)}</Select></div>
        </div>
        <Button className="mt-5" onClick={() => save()} loading={saving}>Save profile</Button>
      </Section>

      <Section icon={GraduationCap} title="Examinations" id="exams" action={<Link href="/onboarding?add=1" className={buttonClass("soft", "sm")}><Plus className="h-4 w-4" /> Add exam</Link>}>
        <div className="space-y-3">
          {exams.map((x) => (
            <div key={x.id} className="flex flex-col gap-3 rounded-2xl border border-line p-4 sm:flex-row sm:items-center">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white" style={{ background: x.examination.color }}><GraduationCap className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <p className="font-bold">{x.examination.name} {x.id === me.profile.active_student_exam && <Badge className="ml-1">Active</Badge>} {x.onboarding_step !== "done" && <Badge tone="amber" className="ml-1">Setup incomplete</Badge>}</p>
                <p className="text-sm text-muted">{x.exam_date ? fmtDate(x.exam_date) : "No date"} · {x.subjects.length} subjects · {x.daily_minutes} min/day</p>
              </div>
              <div className="flex gap-2">
                {x.onboarding_step !== "done" ? <Link href={`/onboarding?se=${x.id}`} className={buttonClass("primary", "sm")}>Finish setup</Link>
                  : <Button size="sm" variant="secondary" onClick={() => setEditing(x)}>Edit</Button>}
                {exams.length > 1 && <Button size="icon" variant="ghost" onClick={() => setArchive(x)} aria-label={`Remove ${x.examination.name}`}><Trash2 className="h-4 w-4" /></Button>}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section icon={Bell} title="Notifications">
        {[["notify_streak", "Streak reminders", "A nudge in the evening if you haven't studied yet."],
          ["notify_email_reminders", "Email reminders", "Occasional emails about streaks and your roadmap."],
          ["notify_product", "Product news", "New features and exam tips."]].map(([k, t, d]) => (
          <div key={k} className="flex items-center justify-between gap-4 border-b border-line py-3.5 last:border-0">
            <div><p className="font-semibold">{t}</p><p className="text-sm text-muted">{d}</p></div>
            <Switch checked={!!form[k]} onChange={toggle(k)} label={t} />
          </div>
        ))}
      </Section>

      <Section icon={Lock} title="Privacy" id="privacy">
        <p className="mb-3 text-sm text-muted">How you appear on leaderboards. Your email is never shown to other students.</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {[["public", "Show my display name"], ["anonymous", "Appear anonymous"], ["hidden", "Hide me completely"]].map(([v, l]) => (
            <button key={v} onClick={() => { const next = { ...form, leaderboard_visibility: v }; setForm(next); save(next); }}
              className={cn("flex items-center justify-between rounded-xl border-2 px-4 py-3 text-left text-sm font-semibold", form.leaderboard_visibility === v ? "border-brand-600 bg-brand-50" : "border-line")}>
              {l}{form.leaderboard_visibility === v && <Check className="h-4 w-4 text-brand-600" />}
            </button>
          ))}
        </div>
      </Section>

      <Section icon={Gift} title="Referrals">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <p className="text-sm">Your referral code: <span className="font-mono text-base font-bold tracking-widest">{me.referral_code}</span></p>
          <Link href="/app/referrals" className={buttonClass("secondary", "sm")}>Open referral dashboard</Link>
        </div>
      </Section>

      <Section icon={ShieldCheck} title="Account security">
        <p className="text-sm text-muted">Kwado AI uses passwordless sign-in: each time you log in we email you a one-time code that expires in 5 minutes. There&apos;s no password to steal. Signing out removes this device&apos;s session.</p>
        <Button variant="danger" className="mt-4" onClick={async () => { await signOut(); router.replace("/"); }}><LogOut className="h-4 w-4" /> Log out</Button>
      </Section>

      {editing && <EditExam se={editing} onClose={() => setEditing(null)} onSaved={async () => { await reload(); setEditing(null); toast({ tone: "success", title: "Examination updated" }); }} />}
      <ConfirmDialog open={!!archive} onClose={() => setArchive(null)} danger confirmLabel="Remove" title={`Remove ${archive?.examination.name}?`}
        body="Your progress is kept — re-adding this exam later restores it." onConfirm={async () => { await api(`/student-exams/${archive!.id}/archive`, { method: "POST" }); await reload(); setArchive(null); }} />
    </div>
  );
}

function Section({ icon: Icon, title, children, id, action }: { icon: any; title: string; children: React.ReactNode; id?: string; action?: React.ReactNode }) {
  return (
    <section id={id} className="card scroll-mt-24 p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between"><h2 className="flex items-center gap-2 text-lg font-bold"><Icon className="h-5 w-5 text-brand-600" /> {title}</h2>{action}</div>
      {children}
    </section>
  );
}

function EditExam({ se, onClose, onSaved }: { se: StudentExam; onClose: () => void; onSaved: () => void }) {
  const { data: exams } = useSWR<Examination[]>("/examinations");
  const exam = exams?.find((e) => e.id === se.examination.id) ?? se.examination;
  const [date, setDate] = useState(se.exam_date ?? "");
  const [minutes, setMinutes] = useState(se.daily_minutes);
  const [subjects, setSubjects] = useState(se.subjects.map((s) => s.id));
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true); setErr("");
    try { await api(`/student-exams/${se.id}`, { method: "PATCH", json: { exam_date: date || null, daily_minutes: minutes, subject_ids: subjects } }); onSaved(); }
    catch (e) { setErr((e as ApiError).message); } finally { setBusy(false); }
  }
  return (
    <Modal open onClose={onClose} title={`Edit ${se.examination.name}`} className="sm:max-w-xl">
      <div className="grid gap-4 sm:grid-cols-2">
        <div><Label>Exam date</Label><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
        <div><Label>Daily study time</Label><Select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>{[15, 30, 45, 60, 90, 120].map((m) => <option key={m} value={m}>{m} minutes</option>)}</Select></div>
      </div>
      <Label className="mt-5">Subjects <span className="font-normal text-muted">({exam.min_subjects === exam.max_subjects ? exam.min_subjects : `${exam.min_subjects}–${exam.max_subjects}`} required)</span></Label>
      <div className="grid max-h-64 grid-cols-2 gap-2 overflow-y-auto">
        {exam.subjects?.map(({ subject: s, is_compulsory }) => {
          const on = subjects.includes(s.id);
          return (
            <button key={s.id} disabled={is_compulsory} onClick={() => setSubjects((x) => on ? x.filter((i) => i !== s.id) : [...x, s.id])}
              className={cn("flex items-center gap-2 rounded-xl border-2 px-3 py-2 text-left text-sm font-semibold", on ? "border-brand-600 bg-brand-50" : "border-line")}>
              <DynIcon name={s.icon} className="h-4 w-4 shrink-0" /> <span className="truncate">{s.name}</span>{is_compulsory && <Lock className="ml-auto h-3.5 w-3.5 shrink-0 text-muted" />}
            </button>
          );
        })}
      </div>
      {err && <p className="mt-3 text-sm font-semibold text-red-600">{err}</p>}
      <p className="mt-3 text-xs text-muted">Changing subjects or date? Regenerate your roadmap afterwards so it reflects the change.</p>
      <div className="mt-5 flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={save} loading={busy}>Save changes</Button></div>
    </Modal>
  );
}
