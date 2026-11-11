"use client";
import "./globals.css";
import { ErrorScreen } from "@/components/app/error-screen";

// Catches errors in the root layout itself, so it must render its own <html>/<body>.
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en-NG">
      <body className="bg-canvas">
        <ErrorScreen error={error} reset={reset} />
      </body>
    </html>
  );
}
