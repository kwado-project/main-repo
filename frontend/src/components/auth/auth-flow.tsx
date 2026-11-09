"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, BadgeCheck, Gift, Mail, ShieldCheck, Sparkles, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FieldError, Input, Label } from "@/components/ui/primitives";
import { OTPInput } from "@/components/ui/otp-input";
import { Logo, LogoMark } from "@/components/ui/logo";
import { CreditCoin, Flame, fireConfetti } from "@/components/ui/fun";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Me } from "@/lib/types";

const emailSchema = z.object({
  email: z.string().trim().min(1, "Enter your email address").email("Enter a valid email address"),
  full_name: z.string().trim().max(120).optional(),
  referral_code: z.string().trim().max(12).optional(),
});
type EmailForm = z.infer<typeof emailSchema>;

export function AuthFlow({ intent }: { intent: "register" | "login" }) {
  const router = useRouter();
  const params = useSearchParams();
  const { signIn, me } = useAuth();
  const [step, setStep] = useState<"email" | "code" | "done">("email");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [resendIn, setResendIn] = useState(0);
  const [isNew, setIsNew] = useState(false);

  const form = useForm<EmailForm>({ resolver: zodResolver(emailSchema), defaultValues: { referral_code: params.get("ref") ?? "" } });

  useEffect(() => {
    if (me && step === "email") router.replace("/app");
  }, [me, step, router]);

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  async function requestCode(values: EmailForm) {
    setError(null);
    try {
      const d = await api<{ resend_in: number; dev_code?: string }>("/auth/otp/request", {
        method: "POST", json: { email: values.email, intent, referral_code: values.referral_code || "" },
      });
      setEmail(values.email.trim().toLowerCase());
      setName(values.full_name ?? "");
      setResendIn(d.resend_in ?? 60);
      setDevCode(d.dev_code ?? null);
      setCode("");
      setStep("code");
    } catch (e) {
      const err = e as ApiError;
      if (err.status === 429 && err.data?.resend_in) {
        setEmail(values.email.trim().toLowerCase());
        setResendIn(err.data.resend_in);
        setStep("code");
        return;
      }
      setError(err.message);
    }
  }

  async function verify(c = code) {
    if (c.length !== 6 || verifying) return;
    setVerifying(true);
    setError(null);
    try {
      const d = await api<{ access: string; user: Me; is_new: boolean }>("/auth/otp/verify", {
        method: "POST", json: { email, code: c, full_name: name },
      });
      setIsNew(d.is_new);
      setStep("done");
      if (d.is_new) fireConfetti({ big: true });
      setTimeout(() => {
        signIn(d.access, d.user);
        const next = params.get("next");
        const needsOnboarding = d.is_new || d.user.student_exams.length === 0 || !d.user.profile.onboarding_completed;
        if (d.user.role !== "student" && !d.is_new) router.replace(next || "/admin");
        else router.replace(needsOnboarding ? "/onboarding" : next && next.startsWith("/") ? next : "/app");
      }, d.is_new ? 2200 : 1100);
    } catch (e) {
      setError((e as ApiError).message);
      setCode("");
    } finally {
      setVerifying(false);
    }
  }

  const isRegister = intent === "register";

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      <BrandPanel isRegister={isRegister} />
      <main className="flex min-h-dvh flex-col bg-white px-5 py-6 sm:px-10 lg:min-h-0 lg:bg-canvas">
        <div className="flex items-center justify-between lg:hidden"><Logo /></div>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-[420px]">
            <AnimatePresence mode="wait">
              {step === "email" && (
                <motion.div key="email" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="lg:card lg:p-8">
                  <div className="mb-7">
                    <div className="mb-5 hidden lg:block"><LogoMark size={44} /></div>
                    <h1 className="text-[1.75rem] font-extrabold leading-tight">{isRegister ? "Create your free account" : "Welcome back"}</h1>
                    <p className="mt-2 text-muted">{isRegister ? "Start with 100 free credits. No password needed." : "Enter your email and we'll send you a sign-in code."}</p>
                  </div>
                  <form onSubmit={form.handleSubmit(requestCode)} className="space-y-4" noValidate>
                    {isRegister && (
                      <div>
                        <Label htmlFor="full_name">Your name <span className="font-normal text-muted">(optional)</span></Label>
                        <Input id="full_name" autoComplete="name" placeholder="e.g. Amaka Okafor" {...form.register("full_name")} />
                      </div>
                    )}
                    <div>
                      <Label htmlFor="email">Email address</Label>
                      <div className="relative">
                        <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                        <Input id="email" type="email" inputMode="email" autoComplete="email" autoFocus placeholder="you@example.com" className="pl-11"
                          invalid={!!form.formState.errors.email} {...form.register("email")} />
                      </div>
                      <FieldError>{form.formState.errors.email?.message}</FieldError>
                    </div>
                    {isRegister && (
                      <div>
                        <Label htmlFor="referral_code">Referral code <span className="font-normal text-muted">(optional)</span></Label>
                        <Input id="referral_code" placeholder="e.g. 7KX3PQ9A" className="uppercase" {...form.register("referral_code")} />
                      </div>
                    )}
                    <FieldError>{error}</FieldError>
                    <Button type="submit" size="lg" className="w-full" loading={form.formState.isSubmitting}>
                      {isRegister ? "Send my code" : "Send sign-in code"} <ArrowRight className="h-5 w-5" />
                    </Button>
                  </form>
                  <p className="mt-6 text-center text-sm text-muted">
                    {isRegister ? "Already have an account? " : "New to Kwado AI? "}
                    <Link href={isRegister ? "/login" : "/register"} className="font-semibold text-brand-700 hover:underline">{isRegister ? "Log in" : "Create a free account"}</Link>
                  </p>
                  {isRegister && <p className="mt-4 text-center text-xs text-muted">By continuing you agree to our <Link href="/legal/terms" className="underline">Terms</Link> and <Link href="/legal/privacy" className="underline">Privacy policy</Link>.</p>}
                </motion.div>
              )}

              {step === "code" && (
                <motion.div key="code" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="lg:card lg:p-8">
                  <button onClick={() => { setStep("email"); setError(null); }} className="mb-6 inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink">
                    <ArrowLeft className="h-4 w-4" /> Change email
                  </button>
                  <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><Mail className="h-7 w-7" /></div>
                  <h1 className="text-[1.75rem] font-extrabold leading-tight">Check your email</h1>
                  <p className="mt-2 text-muted">We sent a 6-digit code to <span className="font-semibold text-ink">{email}</span>. It expires in 5 minutes.</p>
                  {devCode && (
                    <p className="mt-4 rounded-xl border border-dashed border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      <b>Development mode:</b> email isn&apos;t configured, so your code is <b className="tracking-widest">{devCode}</b>.
                    </p>
                  )}
                  <div className="mt-7">
                    <OTPInput value={code} onChange={(v) => { setCode(v); setError(null); }} onComplete={(v) => verify(v)} invalid={!!error} disabled={verifying} />
                  </div>
                  <div className="mt-3 min-h-6 text-center"><FieldError>{error}</FieldError></div>
                  <Button size="lg" className="mt-2 w-full" onClick={() => verify()} loading={verifying} disabled={code.length !== 6}>
                    Verify and continue
                  </Button>
                  <div className="mt-5 text-center text-sm text-muted">
                    Didn&apos;t get it? Check spam, or{" "}
                    {resendIn > 0 ? (
                      <span>resend in <span className="font-semibold tabular-nums text-ink">0:{String(resendIn).padStart(2, "0")}</span></span>
                    ) : (
                      <button className="font-semibold text-brand-700 hover:underline" onClick={() => requestCode({ email, full_name: name, referral_code: form.getValues("referral_code") })}>resend code</button>
                    )}
                  </div>
                </motion.div>
              )}

              {step === "done" && (
                <motion.div key="done" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 15 }}
                    className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-brand-600 text-white shadow-glow">
                    <svg viewBox="0 0 24 24" className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                      <motion.path d="M5 12.5l4.5 4.5L19 7.5" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.25, duration: 0.5 }} />
                    </svg>
                  </motion.div>
                  <h1 className="mt-6 text-2xl font-extrabold">{isNew ? "Welcome to Kwado AI!" : "You're in!"}</h1>
                  {isNew ? (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
                      className="mx-auto mt-5 flex w-fit items-center gap-3 rounded-2xl bg-ink px-5 py-3 text-white">
                      <CreditCoin size={28} /><div className="text-left"><p className="text-xl font-extrabold">+100 credits</p><p className="text-xs text-white/60">Your welcome bonus</p></div>
                    </motion.div>
                  ) : <p className="mt-2 text-muted">Taking you to your dashboard…</p>}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
        <p className="flex items-center justify-center gap-1.5 text-xs text-muted"><ShieldCheck className="h-4 w-4 text-brand-600" /> Secure, passwordless sign-in</p>
      </main>
    </div>
  );
}

function BrandPanel({ isRegister }: { isRegister: boolean }) {
  const points = [
    { icon: Gift, t: "100 free credits", b: "Try diagnostics, quizzes and the AI tutor on us." },
    { icon: Sparkles, t: "A personal roadmap", b: "Built around your weak topics and exam date." },
    { icon: Trophy, t: "Streaks, XP and badges", b: "Make studying a daily habit you enjoy." },
  ];
  return (
    <aside className="relative hidden overflow-hidden bg-ink-deep p-10 text-white lg:flex lg:flex-col xl:p-14">
      <div className="absolute inset-0 grid-bg-dark" />
      <div className="absolute -left-24 bottom-0 h-96 w-96 rounded-full bg-brand-600/40 blur-[110px]" />
      <div className="relative"><Logo dark /></div>
      <div className="relative my-auto max-w-lg py-12">
        <p className="eyebrow text-brand-400">Learn. Play. Practise. Pass.</p>
        <h2 className="mt-4 text-4xl font-extrabold leading-tight xl:text-5xl">{isRegister ? "Every mistake is a lesson." : "Your streak is waiting."}</h2>
        <p className="mt-4 text-lg text-white/65">{isRegister ? "Every lesson brings you closer to success." : "Pick up right where you left off — your roadmap has today's tasks ready."}</p>
        <ul className="mt-10 space-y-5">
          {points.map((p, i) => (
            <motion.li key={p.t} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 + i * 0.1 }} className="flex gap-4">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-brand-400"><p.icon className="h-5 w-5" /></span>
              <div><p className="font-bold">{p.t}</p><p className="text-sm text-white/60">{p.b}</p></div>
            </motion.li>
          ))}
        </ul>
      </div>
      <motion.div className="relative flex w-fit items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur" animate={{ y: [0, -6, 0] }} transition={{ duration: 5, repeat: Infinity }}>
        <Flame size={34} />
        <div><p className="font-bold">“The streaks kept me going every day.”</p><p className="text-xs text-white/50">Sample student story</p></div>
        <BadgeCheck className="h-5 w-5 text-brand-400" />
      </motion.div>
    </aside>
  );
}
