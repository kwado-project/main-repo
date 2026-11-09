import Link from "next/link";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-glow"><Compass className="h-8 w-8" /></div>
      <h1 className="mt-6 text-3xl font-extrabold">This page took a wrong turn</h1>
      <p className="mt-2 text-muted">Let&apos;s get you back to learning.</p>
      <Link href="/" className="mt-6 rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white">Go home</Link>
    </div>
  );
}
