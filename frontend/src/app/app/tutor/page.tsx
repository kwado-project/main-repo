"use client";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR, { useSWRConfig } from "swr";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Bot, Check, Copy, History, MessageSquarePlus, RefreshCw, Sparkles, Square, Trash2, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Skeleton } from "@/components/ui/primitives";
import { Drawer } from "@/components/ui/overlay";
import { Markdown } from "@/components/ui/markdown";
import { CreditCoin } from "@/components/ui/fun";
import { useToast } from "@/components/ui/toast";
import { api, ApiError, streamSSE } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Pricing } from "@/lib/types";
import { cn, fmtDate, uid } from "@/lib/utils";

type Msg = { id: number | string; role: "user" | "assistant"; content: string; status?: string; is_mock?: boolean; streaming?: boolean; failed?: boolean };
type Conv = { id: number; title: string; subject_name: string | null; topic_name: string | null; updated_at: string };

const STARTERS = [
  "Explain quadratic equations simply.",
  "Give me five JAMB-style questions on genetics.",
  "Why is my answer incorrect?",
  "Teach me this topic step by step.",
];
const PURPOSES = [
  { key: "tutor_chat", label: "Ask", pricing: "ai_tutor_response" },
  { key: "topic_explanation", label: "Explain topic", pricing: "ai_topic_explanation" },
  { key: "practice_set", label: "Practice set", pricing: "ai_practice_set" },
] as const;

export default function TutorPage() {
  return <Suspense><Tutor /></Suspense>;
}

function Tutor() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { me } = useAuth();
  const { mutate } = useSWRConfig();
  const { data: convs, mutate: mutateConvs } = useSWR<{ results: Conv[] }>("/ai/conversations");
  const { data: pricing } = useSWR<Pricing[]>("/wallet/pricing");
  const { data: wallet, mutate: mutateWallet } = useSWR<any>("/wallet");
  const [active, setActive] = useState<number | null>(null);
  const [meta, setMeta] = useState<any>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [purpose, setPurpose] = useState<(typeof PURPOSES)[number]["key"]>("tutor_chat");
  const [streaming, setStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const booted = useRef(false);

  const cost = pricing?.find((p) => p.key === PURPOSES.find((x) => x.key === purpose)!.pricing)?.credits ?? 2;
  const balance = wallet?.balance ?? me?.balance ?? 0;
  const se = me?.student_exams.find((x) => x.id === me.profile.active_student_exam);

  const open = useCallback(async (id: number) => {
    setLoadingConv(true);
    setActive(id);
    setHistoryOpen(false);
    try {
      const c = await api<any>(`/ai/conversations/${id}`);
      setMeta(c);
      setMessages(c.messages.filter((m: any) => m.status !== "failed" || m.role === "user"));
      setSuggestions([]);
    } finally {
      setLoadingConv(false);
    }
  }, []);

  // Deep links: ?subject=&topic=&question=&prompt=
  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    const subject = params.get("subject"), topic = params.get("topic"), question = params.get("question"), prompt = params.get("prompt");
    if (subject || topic || question) {
      api<any>("/ai/conversations", { method: "POST", json: { subject: subject ? Number(subject) : null, topic: topic ? Number(topic) : null, question: question ? Number(question) : null } })
        .then((c) => { setActive(c.id); setMeta(c); setMessages([]); mutateConvs(); })
        .catch(() => {});
    }
    if (prompt) setInput(prompt);
    router.replace("/app/tutor");
  }, [params, router, mutateConvs]);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages]);
  useEffect(() => {
    const t = textarea.current;
    if (t) { t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 180) + "px"; }
  }, [input]);

  function newConversation() {
    abort.current?.abort();
    setActive(null); setMeta(null); setMessages([]); setSuggestions([]); setInput(""); setHistoryOpen(false);
    textarea.current?.focus();
  }

  async function send(text = input) {
    const content = text.trim();
    if (!content || streaming) return;
    if (balance < cost) { toast({ tone: "error", title: "Not enough credits", body: `This needs ${cost} credits. Top up your wallet to continue.` }); return; }
    let convId = active;
    if (!convId) {
      const c = await api<any>("/ai/conversations", { method: "POST", json: {} });
      convId = c.id; setActive(c.id); setMeta(c);
    }
    setInput("");
    setSuggestions([]);
    const userMsg: Msg = { id: uid(), role: "user", content };
    const aiId = uid();
    setMessages((m) => [...m, userMsg, { id: aiId, role: "assistant", content: "", streaming: true }]);
    setStreaming(true);
    abort.current = new AbortController();
    try {
      await streamSSE(`/ai/conversations/${convId}/messages`, { content, purpose, idempotency_key: uid() }, (ev, data) => {
        if (ev === "delta") setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, content: x.content + data.text } : x)));
        if (ev === "done") {
          setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, id: data.message_id, streaming: false, is_mock: data.is_mock } : x)));
          setSuggestions(data.suggestions ?? []);
          mutateWallet({ ...(wallet ?? {}), balance: data.balance }, { revalidate: false });
          mutate("/gamification/missions");
        }
        if (ev === "error") {
          setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, streaming: false, failed: true, content: data.detail } : x)));
          mutateWallet();
          toast({ tone: "info", title: "Credits refunded", body: `${data.refunded} credits returned to your wallet.` });
        }
      }, abort.current.signal);
    } catch (e) {
      const err = e as ApiError;
      if ((e as Error).name === "AbortError") {
        setMessages((m) => m.map((x) => (x.id === aiId ? { ...x, streaming: false, failed: true, content: x.content || "Stopped. You weren't charged for this answer." } : x)));
        setTimeout(() => mutateWallet(), 800);
      } else {
        setMessages((m) => m.filter((x) => x.id !== aiId));
        toast({ tone: "error", title: err.status === 402 ? "Not enough credits" : "Couldn't send", body: err.message });
        setInput(content);
      }
    } finally {
      setStreaming(false);
      mutateConvs();
    }
  }

  async function remove(id: number) {
    await api(`/ai/conversations/${id}`, { method: "DELETE" });
    if (active === id) newConversation();
    mutateConvs();
  }

  const list = (
    <div className="flex h-full flex-col">
      <div className="p-3"><Button onClick={newConversation} className="w-full" variant="secondary"><MessageSquarePlus className="h-4 w-4" /> New conversation</Button></div>
      <p className="px-4 pb-2 text-xs font-bold uppercase tracking-wider text-muted">History</p>
      <ul className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
        {!convs && [0, 1, 2].map((i) => <li key={i} className="px-2 py-1"><Skeleton className="h-11" /></li>)}
        {convs?.results?.length === 0 && <li className="px-3 py-6 text-center text-sm text-muted">Your conversations will appear here.</li>}
        {convs?.results?.map((c) => (
          <li key={c.id} className="group relative">
            <button onClick={() => open(c.id)} className={cn("w-full rounded-xl px-3 py-2.5 text-left transition", active === c.id ? "bg-brand-50 ring-1 ring-brand-100" : "hover:bg-slate-50")}>
              <p className="truncate pr-6 text-sm font-semibold">{c.title}</p>
              <p className="truncate text-xs text-muted">{[c.subject_name, c.topic_name].filter(Boolean).join(" · ") || fmtDate(c.updated_at)}</p>
            </button>
            <button onClick={() => remove(c.id)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100" aria-label={`Delete ${c.title}`}><Trash2 className="h-4 w-4" /></button>
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="-mx-4 -mb-28 -mt-5 flex h-[calc(100dvh-64px-68px)] sm:-mx-6 lg:-mx-8 lg:-mb-12 lg:-mt-8 lg:h-[calc(100dvh-72px)]">
      <aside className="hidden w-72 shrink-0 border-r border-line bg-white md:block">{list}</aside>
      <section className="flex min-w-0 flex-1 flex-col">
        {/* context bar */}
        <div className="flex items-center gap-2 border-b border-line bg-white/70 px-4 py-2.5 backdrop-blur">
          <button onClick={() => setHistoryOpen(true)} className="rounded-lg p-1.5 text-muted hover:bg-slate-100 md:hidden" aria-label="Conversation history"><History className="h-5 w-5" /></button>
          <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto scrollbar-none">
            {se && <Badge tone="dark">{se.examination.name}</Badge>}
            {meta?.subject_name && <Badge>{meta.subject_name}</Badge>}
            {meta?.topic_name && <Badge tone="gray">{meta.topic_name}</Badge>}
            {meta?.question && <Badge tone="amber">About a question</Badge>}
          </div>
          <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-muted" title="Your credit balance"><CreditCoin size={14} />{balance}</span>
          <button onClick={newConversation} className="rounded-lg p-1.5 text-muted hover:bg-slate-100 md:hidden" aria-label="New conversation"><MessageSquarePlus className="h-5 w-5" /></button>
        </div>

        {/* messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-3xl space-y-5">
            {loadingConv && <Skeleton className="h-24" />}
            {!loadingConv && messages.length === 0 && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center pt-6 text-center sm:pt-12">
                <div className="relative"><div className="absolute inset-0 scale-150 rounded-full bg-brand-200 blur-2xl" /><span className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-glow"><Bot className="h-8 w-8" /></span></div>
                <h1 className="mt-5 text-2xl font-extrabold">How can I help you study?</h1>
                <p className="mt-1 max-w-md text-muted">Ask about any topic{se ? ` in your ${se.examination.name} subjects` : ""}. I&apos;ll explain step by step.</p>
                <div className="mt-7 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                  {STARTERS.map((s) => (
                    <button key={s} onClick={() => send(s)} className="rounded-2xl border border-line bg-white px-4 py-3 text-left text-sm font-semibold transition hover:border-brand-300 hover:bg-brand-50">{s}</button>
                  ))}
                </div>
              </motion.div>
            )}
            <AnimatePresence initial={false}>
              {messages.map((m) => <Bubble key={m.id} m={m} onRetry={() => { const last = [...messages].reverse().find((x) => x.role === "user"); if (last) send(last.content); }} />)}
            </AnimatePresence>
            {suggestions.length > 0 && !streaming && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-wrap gap-2 pl-11">
                {suggestions.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-brand-200 bg-white px-3.5 py-1.5 text-sm font-semibold text-brand-800 hover:bg-brand-50">{s}</button>)}
              </motion.div>
            )}
            <div ref={bottom} />
          </div>
        </div>

        {/* composer */}
        <div className="border-t border-line bg-white px-3 pb-3 pt-2.5 sm:px-4">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex items-center gap-1.5 overflow-x-auto scrollbar-none">
              {PURPOSES.map((p) => (
                <button key={p.key} onClick={() => setPurpose(p.key)} className={cn("flex shrink-0 items-center gap-1 rounded-full px-3 py-1 text-xs font-bold transition", purpose === p.key ? "bg-ink text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200")}>
                  {p.key === "practice_set" ? <Wand2 className="h-3.5 w-3.5" /> : p.key === "topic_explanation" ? <Sparkles className="h-3.5 w-3.5" /> : null}{p.label}
                </button>
              ))}
            </div>
            <div className="flex items-end gap-2 rounded-2xl border border-line bg-canvas p-2 focus-within:border-brand-400 focus-within:ring-4 focus-within:ring-brand-100">
              <textarea ref={textarea} value={input} onChange={(e) => setInput(e.target.value)} rows={1} maxLength={4000}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                placeholder={purpose === "practice_set" ? "Which topic? e.g. Genetics" : purpose === "topic_explanation" ? "Which topic should I teach? e.g. Osmosis" : "Ask anything…"}
                className="max-h-[180px] min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-[15px] focus:outline-none" aria-label="Message the tutor" />
              {streaming ? (
                <button onClick={() => abort.current?.abort()} className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-white" aria-label="Stop"><Square className="h-4 w-4 fill-current" /></button>
              ) : (
                <button onClick={() => send()} disabled={!input.trim()} className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-press transition disabled:bg-slate-300 disabled:shadow-none" aria-label="Send"><ArrowUp className="h-5 w-5" /></button>
              )}
            </div>
            <p className="mt-1.5 flex items-center justify-center gap-1 text-[11px] text-muted">
              <CreditCoin size={12} /> {cost} credit{cost === 1 ? "" : "s"} per answer · charged only if the answer completes · AI can make mistakes
            </p>
          </div>
        </div>
      </section>
      <Drawer open={historyOpen} onClose={() => setHistoryOpen(false)} side="left" title="Conversations">{list}</Drawer>
    </div>
  );
}

function Bubble({ m, onRetry }: { m: Msg; onRetry: () => void }) {
  const [copied, setCopied] = useState(false);
  if (m.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-[15px] text-white">{m.content}</div>
      </motion.div>
    );
  }
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-xl", m.failed ? "bg-red-100 text-red-600" : "bg-ink text-white")}><Bot className="h-4 w-4" /></span>
      <div className="min-w-0 flex-1">
        {m.streaming && !m.content ? (
          <div className="flex w-fit gap-1.5 rounded-2xl bg-white px-4 py-3 ring-1 ring-line" aria-label="Tutor is typing">
            {[0, 1, 2].map((i) => <motion.span key={i} className="h-2 w-2 rounded-full bg-slate-400" animate={{ y: [0, -5, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }} />)}
          </div>
        ) : m.failed ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {m.content}
            <button onClick={onRetry} className="ml-2 inline-flex items-center gap-1 font-semibold underline"><RefreshCw className="h-3.5 w-3.5" /> Try again</button>
          </div>
        ) : (
          <div className="rounded-2xl rounded-tl-md bg-white px-4 py-3 ring-1 ring-line">
            <Markdown>{m.content}</Markdown>
            {m.streaming && <span className="inline-block h-4 w-1.5 animate-pulse rounded-sm bg-brand-600 align-middle" />}
          </div>
        )}
        {!m.streaming && !m.failed && m.content && (
          <div className="mt-1.5 flex items-center gap-3 pl-1">
            <button onClick={() => { navigator.clipboard.writeText(m.content); setCopied(true); setTimeout(() => setCopied(false), 1500); }} className="inline-flex items-center gap-1 text-xs font-semibold text-muted hover:text-ink">
              {copied ? <Check className="h-3.5 w-3.5 text-brand-600" /> : <Copy className="h-3.5 w-3.5" />}{copied ? "Copied" : "Copy"}
            </button>
            {m.is_mock && <Badge tone="amber">Dev mode response</Badge>}
          </div>
        )}
      </div>
    </motion.div>
  );
}
