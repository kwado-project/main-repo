"use client";
import { useEffect, useState } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";
import { isStaleDeployError, reloadForNewVersion } from "@/lib/stale-deploy";

export function ErrorScreen({ error, reset }: { error: Error & { digest?: string }; reset?: () => void }) {
  // "stale" stays true only while an automatic reload is actually happening; if we already
  // reloaded in the last minute (a genuinely broken deploy), fall back to the normal error screen.
  const [stale, setStale] = useState(() => isStaleDeployError(error));
  useEffect(() => {
    if (isStaleDeployError(error) && reloadForNewVersion()) return;
    setStale(false);
    console.error(error);
  }, [error]);
  return (
    <div className="flex min-h-[70dvh] flex-col items-center justify-center px-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-50 text-amber-600"><TriangleAlert className="h-8 w-8" /></div>
      <h1 className="mt-6 text-2xl font-extrabold">{stale ? "Updating Kwado AI…" : "Something went wrong on this page"}</h1>
      <p className="mt-2 max-w-md text-muted">{stale ? "A new version was just released. Loading it now." : "Your progress is saved. Try again, or reload the page."}</p>
      {!stale && (
        <>
          <div className="mt-6 flex gap-3">
            {reset && <button onClick={reset} className="rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white">Try again</button>}
            <button onClick={() => window.location.reload()} className="inline-flex items-center gap-2 rounded-xl border border-line bg-white px-5 py-3 font-semibold">
              <RefreshCw className="h-4 w-4" /> Reload
            </button>
          </div>
          <p className="mt-6 max-w-lg break-words font-mono text-xs text-muted">{error.message}{error.digest ? ` (ref ${error.digest})` : ""}</p>
        </>
      )}
    </div>
  );
}
