"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR, { SWRConfig } from "swr";
import { api, fetcher, refreshSession, setAccessToken } from "./api";
import type { Me } from "./types";

type AuthState = {
  me: Me | null | undefined; // undefined = loading
  ready: boolean;
  signIn: (access: string, me: Me) => void;
  signOut: () => Promise<void>;
  reload: () => Promise<any>;
};

const Ctx = createContext<AuthState>({} as AuthState);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const { data: me, mutate } = useSWR<Me>(authed ? "/me" : null, fetcher, { revalidateOnFocus: false });

  useEffect(() => {
    refreshSession().then((ok) => { setAuthed(ok); setReady(true); });
  }, []);

  const signIn = useCallback((access: string, user: Me) => {
    setAccessToken(access);
    setAuthed(true);
    mutate(user, { revalidate: false });
  }, [mutate]);

  const signOut = useCallback(async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => {});
    setAccessToken(null);
    setAuthed(false);
    mutate(undefined, { revalidate: false });
  }, [mutate]);

  const value: AuthState = { me: !ready ? undefined : authed ? me : null, ready, signIn, signOut, reload: () => mutate() };
  return (
    <SWRConfig value={{ fetcher, revalidateOnFocus: false, shouldRetryOnError: false }}>
      <Ctx.Provider value={value}>{children}</Ctx.Provider>
    </SWRConfig>
  );
}

export const useAuth = () => useContext(Ctx);

/** Redirects unauthenticated visitors to /login. Returns the user once loaded. */
export function useRequireAuth(opts: { role?: "admin" | "staff" } = {}) {
  const { me, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!ready) return;
    if (me === null) router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    if (me && opts.role === "admin" && me.role !== "admin") router.replace("/app");
    if (me && opts.role === "staff" && me.role === "student") router.replace("/app");
  }, [me, ready, router, opts.role]);
  return me;
}
