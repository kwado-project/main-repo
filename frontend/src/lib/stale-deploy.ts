// After a new deploy, a tab opened earlier asks for page files (chunks) that no longer exist.
// Detect that and reload once to fetch the new version, instead of showing an error screen.
const KEY = "kwado:reloaded-for-new-version";
const PATTERN = /ChunkLoadError|Loading chunk [\w-]+ failed|Loading CSS chunk|Failed to fetch dynamically imported module|error loading dynamically imported module/i;

export function isStaleDeployError(err: unknown): boolean {
  const msg = err instanceof Error ? `${err.name} ${err.message}` : String(err ?? "");
  return PATTERN.test(msg);
}

/** Reload at most once per minute so a genuinely broken deploy can't loop forever. */
export function reloadForNewVersion(): boolean {
  try {
    const last = Number(sessionStorage.getItem(KEY) || 0);
    if (Date.now() - last < 60_000) return false;
    sessionStorage.setItem(KEY, String(Date.now()));
  } catch {
    /* storage blocked: still reload once */
  }
  window.location.reload();
  return true;
}
