"use client";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMounted } from "./primitives";

function useLockScroll(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [open, onClose]);
}

export function Modal({ open, onClose, title, description, children, className, hideClose }: {
  open: boolean; onClose: () => void; title?: string; description?: string; children: React.ReactNode; className?: string; hideClose?: boolean;
}) {
  const mounted = useMounted();
  useLockScroll(open, onClose);
  if (!mounted) return null;
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[80] flex items-end justify-center sm:items-center" role="dialog" aria-modal="true" aria-label={title}>
          <motion.div className="absolute inset-0 bg-ink-deep/60 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            className={cn("relative z-10 max-h-[92dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-6 shadow-lift sm:max-w-lg sm:rounded-3xl", className)}
            initial={{ y: 40, opacity: 0, scale: 0.98 }} animate={{ y: 0, opacity: 1, scale: 1 }} exit={{ y: 30, opacity: 0, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
          >
            <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-slate-200 sm:hidden" />
            {!hideClose && (
              <button onClick={onClose} aria-label="Close" className="absolute right-4 top-4 rounded-lg p-1.5 text-muted hover:bg-slate-100 hover:text-ink">
                <X className="h-5 w-5" />
              </button>
            )}
            {title && <h2 className="pr-8 text-xl font-bold">{title}</h2>}
            {description && <p className="mt-1 text-sm text-muted">{description}</p>}
            <div className={cn(title && "mt-5")}>{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

export function Drawer({ open, onClose, children, side = "right", className, title }: {
  open: boolean; onClose: () => void; children: React.ReactNode; side?: "left" | "right"; className?: string; title?: string;
}) {
  const mounted = useMounted();
  useLockScroll(open, onClose);
  if (!mounted) return null;
  const x = side === "right" ? "100%" : "-100%";
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[70]" role="dialog" aria-modal="true" aria-label={title}>
          <motion.div className="absolute inset-0 bg-ink-deep/50 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.aside
            className={cn("absolute top-0 h-full w-[86%] max-w-sm overflow-y-auto bg-white shadow-lift", side === "right" ? "right-0" : "left-0", className)}
            initial={{ x }} animate={{ x: 0 }} exit={{ x }} transition={{ type: "spring", stiffness: 380, damping: 38 }}
          >
            {children}
          </motion.aside>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

export function ConfirmDialog({ open, onClose, onConfirm, title, body, confirmLabel = "Confirm", danger, loading, children }: {
  open: boolean; onClose: () => void; onConfirm: () => void; title: string; body?: React.ReactNode; confirmLabel?: string; danger?: boolean; loading?: boolean; children?: React.ReactNode;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      {body && <div className="text-[15px] text-muted">{body}</div>}
      {children}
      <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button onClick={onClose} className="h-11 rounded-xl px-5 font-semibold text-ink hover:bg-slate-100">Cancel</button>
        <button onClick={onConfirm} disabled={loading}
          className={cn("inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 font-semibold text-white shadow-press disabled:opacity-60", danger ? "bg-red-600 hover:bg-red-700" : "bg-brand-600 hover:bg-brand-700")}>
          {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
