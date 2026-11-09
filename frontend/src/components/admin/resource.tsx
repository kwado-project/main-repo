"use client";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { ChevronLeft, ChevronRight, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, EmptyState, Input, Label, Select, Skeleton, Switch, Textarea } from "@/components/ui/primitives";
import { ConfirmDialog, Modal } from "@/components/ui/overlay";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

export type Field = {
  name: string; label: string; type?: "text" | "number" | "textarea" | "bool" | "select" | "json" | "date" | "color";
  options?: { value: string | number; label: string }[]; optionsFrom?: string; optionLabel?: string; required?: boolean; help?: string; full?: boolean;
};
export type Column = { key: string; label: string; render?: (row: any) => React.ReactNode; className?: string };

export function useDebounced<T>(v: T, ms = 300) {
  const [d, setD] = useState(v);
  useEffect(() => { const t = setTimeout(() => setD(v), ms); return () => clearTimeout(t); }, [v, ms]);
  return d;
}

export function StatusBadge({ value }: { value: string }) {
  const tone: any = { published: "green", success: "green", granted: "green", ready: "green", true: "green", active: "green",
    pending: "amber", in_review: "amber", answer_verified: "blue", validated: "blue", processing: "amber",
    draft: "gray", failed: "red", rejected: "red", reversed: "gray", refunded: "blue", abandoned: "gray", false: "gray" }[String(value)] ?? "gray";
  return <Badge tone={tone}>{String(value).replace(/_/g, " ")}</Badge>;
}

export function ResourceTable({ title, endpoint, columns, fields, filters = [], searchable = true, canCreate = true, canEdit = true, canDelete = true,
  rowActions, description, defaults = {} }: {
  title: string; endpoint: string; columns: Column[]; fields?: Field[]; filters?: { name: string; label: string; options: { value: string; label: string }[] }[];
  searchable?: boolean; canCreate?: boolean; canEdit?: boolean; canDelete?: boolean; rowActions?: (row: any, reload: () => void) => React.ReactNode; description?: string; defaults?: Record<string, any>;
}) {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [f, setF] = useState<Record<string, string>>({});
  const dq = useDebounced(q);
  const qs = new URLSearchParams({ page: String(page), ...(dq ? { search: dq } : {}), ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) });
  const { data, mutate, isLoading } = useSWR<any>(`${endpoint}?${qs}`);
  const [edit, setEdit] = useState<any>(null);
  const [del, setDel] = useState<any>(null);
  const toast = useToast();
  useEffect(() => setPage(1), [dq, JSON.stringify(f)]); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = data?.results ?? (Array.isArray(data) ? data : []);
  const count = data?.count ?? rows.length;
  const pages = Math.max(1, Math.ceil(count / 20));

  return (
    <div>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div><h1 className="text-2xl font-extrabold">{title}</h1>{description && <p className="mt-1 text-sm text-muted">{description}</p>}</div>
        {canCreate && fields && <Button onClick={() => setEdit({ ...defaults })}><Plus className="h-4 w-4" /> New</Button>}
      </div>
      <div className="mt-5 flex flex-col gap-2 sm:flex-row">
        {searchable && (
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} className="h-11 pl-10" />
          </div>
        )}
        {filters.map((fl) => (
          <Select key={fl.name} value={f[fl.name] ?? ""} onChange={(e) => setF({ ...f, [fl.name]: e.target.value })} className="sm:w-48" aria-label={fl.label}>
            <option value="">{fl.label}: all</option>
            {fl.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </Select>
        ))}
      </div>
      <div className="card mt-4 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-wider text-muted">
              <tr>{columns.map((c) => <th key={c.key} className={cn("px-4 py-3 font-bold", c.className)}>{c.label}</th>)}<th className="px-4 py-3" /></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {isLoading && [0, 1, 2, 3].map((i) => <tr key={i}><td colSpan={columns.length + 1} className="px-4 py-3"><Skeleton className="h-6" /></td></tr>)}
              {rows.map((r: any) => (
                <tr key={r.id ?? r.key} className="hover:bg-slate-50/60">
                  {columns.map((c) => <td key={c.key} className={cn("px-4 py-3 align-middle", c.className)}>{c.render ? c.render(r) : typeof r[c.key] === "boolean" ? <StatusBadge value={String(r[c.key])} /> : String(r[c.key] ?? "—")}</td>)}
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {rowActions?.(r, () => mutate())}
                      {canEdit && fields && <Button size="icon" variant="ghost" onClick={() => setEdit(r)} aria-label="Edit"><Pencil className="h-4 w-4" /></Button>}
                      {canDelete && <Button size="icon" variant="ghost" onClick={() => setDel(r)} aria-label="Delete"><Trash2 className="h-4 w-4 text-red-500" /></Button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!isLoading && rows.length === 0 && <EmptyState icon={Search} title="Nothing found" body="Try a different search or filter." />}
        <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
          <span className="text-muted">{count} result{count === 1 ? "" : "s"}</span>
          <div className="flex items-center gap-2">
            <Button size="icon" variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></Button>
            <span className="font-semibold">{page} / {pages}</span>
            <Button size="icon" variant="ghost" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Next page"><ChevronRight className="h-4 w-4" /></Button>
          </div>
        </div>
      </div>
      {edit && fields && (
        <ResourceForm title={edit.id ? `Edit ${title.replace(/s$/, "").toLowerCase()}` : `New ${title.replace(/s$/, "").toLowerCase()}`} fields={fields} initial={edit}
          onClose={() => setEdit(null)}
          onSubmit={async (values) => {
            if (edit.id) await api(`${endpoint}/${edit.id}`, { method: "PATCH", json: values });
            else await api(endpoint, { method: "POST", json: values });
            toast({ tone: "success", title: "Saved" });
            setEdit(null); mutate();
          }} />
      )}
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} danger confirmLabel="Delete" title="Delete this record?" body="This can't be undone and is recorded in the audit log."
        onConfirm={async () => { try { await api(`${endpoint}/${del.id}`, { method: "DELETE" }); toast({ tone: "success", title: "Deleted" }); mutate(); } catch (e) { toast({ tone: "error", title: "Couldn't delete", body: (e as ApiError).message }); } setDel(null); }} />
    </div>
  );
}

export function ResourceForm({ title, fields, initial, onSubmit, onClose }: {
  title: string; fields: Field[]; initial: any; onSubmit: (v: any) => Promise<void>; onClose: () => void;
}) {
  const [v, setV] = useState<any>(() => Object.fromEntries(fields.map((f) => [f.name, f.type === "json" ? JSON.stringify(initial[f.name] ?? (f.name === "content" || f.name === "solution_steps" ? [] : {}), null, 2) : initial[f.name] ?? (f.type === "bool" ? false : "")])));
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit() {
    setBusy(true); setErr("");
    try {
      const out: any = {};
      for (const f of fields) {
        let val = v[f.name];
        if (f.type === "json") { try { val = JSON.parse(val || "null"); } catch { throw new Error(`${f.label}: invalid JSON`); } }
        if (f.type === "number") val = val === "" ? null : Number(val);
        if (f.type === "select" && val === "") val = null;
        out[f.name] = val;
      }
      await onSubmit(out);
    } catch (e) { setErr(e instanceof ApiError ? JSON.stringify(e.data) : (e as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal open onClose={onClose} title={title} className="sm:max-w-2xl">
      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map((f) => (
          <div key={f.name} className={cn((f.full || f.type === "textarea" || f.type === "json") && "sm:col-span-2")}>
            {f.type !== "bool" && <Label htmlFor={f.name}>{f.label}{f.required && " *"}</Label>}
            {f.type === "textarea" ? <Textarea id={f.name} rows={4} value={v[f.name]} onChange={(e) => setV({ ...v, [f.name]: e.target.value })} />
              : f.type === "json" ? <Textarea id={f.name} rows={8} className="font-mono text-xs" value={v[f.name]} onChange={(e) => setV({ ...v, [f.name]: e.target.value })} />
              : f.type === "bool" ? <div className="flex items-center justify-between rounded-xl border border-line px-4 py-3"><span className="text-sm font-semibold">{f.label}</span><Switch checked={!!v[f.name]} onChange={(x) => setV({ ...v, [f.name]: x })} label={f.label} /></div>
              : f.type === "select" ? <OptionSelect f={f} value={v[f.name]} onChange={(x) => setV({ ...v, [f.name]: x })} />
              : <Input id={f.name} type={f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "color" ? "color" : "text"} value={v[f.name] ?? ""} onChange={(e) => setV({ ...v, [f.name]: e.target.value })} className={f.type === "color" ? "h-12 p-1" : ""} />}
            {f.help && <p className="mt-1 text-xs text-muted">{f.help}</p>}
          </div>
        ))}
      </div>
      {err && <p className="mt-4 break-words rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{err}</p>}
      <div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={submit} loading={busy}>Save</Button></div>
    </Modal>
  );
}

function OptionSelect({ f, value, onChange }: { f: Field; value: any; onChange: (v: any) => void }) {
  const { data } = useSWR<any>(f.optionsFrom ? `${f.optionsFrom}${f.optionsFrom.includes("?") ? "&" : "?"}page_size=100` : null);
  const opts = f.options ?? (data?.results ?? data ?? []).map((o: any) => ({ value: o.id, label: o[f.optionLabel ?? "name"] }));
  return (
    <Select id={f.name} value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? "" : isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value))}>
      <option value="">—</option>
      {opts.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </Select>
  );
}
