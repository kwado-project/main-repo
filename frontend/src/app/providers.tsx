"use client";
import { useEffect } from "react";
import { MotionConfig } from "framer-motion";
import { isStaleDeployError, reloadForNewVersion } from "@/lib/stale-deploy";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/components/ui/toast";

export function Providers({ children }: { children: React.ReactNode }) {
  // A tab opened before a deploy fails to load the new page files during navigation: reload once.
  useEffect(() => {
    const onError = (e: ErrorEvent) => isStaleDeployError(e.error ?? e.message) && reloadForNewVersion();
    const onRejection = (e: PromiseRejectionEvent) => isStaleDeployError(e.reason) && reloadForNewVersion();
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
  return (
    <MotionConfig reducedMotion="user">
      <AuthProvider>
        <ToastProvider>{children}</ToastProvider>
      </AuthProvider>
    </MotionConfig>
  );
}
