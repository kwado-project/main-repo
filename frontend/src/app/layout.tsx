import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "Kwado AI — Learn. Play. Practise. Pass.", template: "%s · Kwado AI" },
  description:
    "Personalised, AI-powered exam preparation for JAMB, WAEC, NECO, GCE, NABTEB and Post-UTME. Every mistake is a lesson. Every lesson brings you closer to success.",
  applicationName: "Kwado AI",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = { themeColor: "#16A34A", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-NG">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
