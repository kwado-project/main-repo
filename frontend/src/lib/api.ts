// Same-origin API client. The access token lives only in memory; the refresh
// token is an httpOnly cookie scoped to /api/auth/ (never readable from JS).
let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;

export function setAccessToken(t: string | null) {
  accessToken = t;
}
export function getAccessToken() {
  return accessToken;
}

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(status: number, data: any) {
    super(extractMessage(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
  get code(): string | undefined {
    return this.data?.code ?? this.data?.detail?.code;
  }
}

export function extractMessage(data: any): string {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (typeof data.detail === "string") return data.detail;
  if (data.detail?.detail) return data.detail.detail;
  if (Array.isArray(data.detail)) return data.detail.join(" ");
  const first = Object.values(data).find((v) => Array.isArray(v) || typeof v === "string");
  if (Array.isArray(first)) return String(first[0]);
  if (typeof first === "string") return first;
  return "";
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" })
      .then(async (r) => {
        if (!r.ok) {
          accessToken = null;
          return false;
        }
        const d = await r.json();
        accessToken = d.access;
        return true;
      })
      .catch(() => false)
      .finally(() => {
        setTimeout(() => (refreshing = null), 0);
      });
  }
  return refreshing;
}

function url(path: string) {
  return path.startsWith("/api") ? path : `/api${path}`;
}

export async function rawFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(url(path), { ...init, headers, credentials: "same-origin" });
  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshSession()) return rawFetch(path, init, false);
  }
  return res;
}

export async function api<T = any>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init;
  const res = await rawFetch(path, { ...rest, body: json !== undefined ? JSON.stringify(json) : rest.body });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

function safeJson(t: string) {
  try {
    return JSON.parse(t);
  } catch {
    return t;
  }
}

export const fetcher = (path: string) => api(path);

/** Server-sent events over POST (fetch streaming). */
export async function streamSSE(
  path: string,
  body: unknown,
  onEvent: (event: string, data: any) => void,
  signal?: AbortSignal,
) {
  const res = await rawFetch(path, { method: "POST", body: JSON.stringify(body), signal });
  if (!res.ok || !res.body) {
    const t = await res.text();
    throw new ApiError(res.status, t ? safeJson(t) : null);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, i);
      buf = buf.slice(i + 2);
      let ev = "message";
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event: ")) ev = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      onEvent(ev, data ? safeJson(data) : null);
    }
  }
}
