import Link from "next/link";
import { notFound } from "next/navigation";
import { Logo } from "@/components/ui/logo";

const DOCS: Record<string, { title: string; sections: [string, string][] }> = {
  privacy: {
    title: "Privacy policy",
    sections: [
      ["What we collect", "Your email address, the examinations and subjects you choose, your learning activity (answers, scores, XP), files you upload, and payment records from Paystack. We never receive or store your card details."],
      ["How we use it", "To run your account, personalise your study roadmap, mark your work, process payments and referral rewards, and keep the service secure. We do not sell personal data."],
      ["Your documents", "Uploaded materials are private to you by default, stored encrypted in private object storage and only accessible through short-lived links after we check you own them."],
      ["Children and young people", "Many of our students are under 18. We collect the minimum data needed, keep the tutor education-focused, let students hide from leaderboards, and never show other students' emails."],
      ["Your rights", "Under the Nigeria Data Protection Act 2023 you can access, correct, export or delete your data. Email privacy@kwado.ai and we will respond within 30 days."],
    ],
  },
  terms: {
    title: "Terms of use",
    sections: [
      ["Credits", "Credits are prepaid units for using paid activities (1 credit = ₦10). They are not cash, cannot be withdrawn, and are only awarded after a payment is verified with our payment provider."],
      ["Referral rewards", "Referrers receive 20% of the credits purchased by students they referred. Rewards are reversed if the purchase is refunded or charged back. Self-referrals and abuse are not allowed."],
      ["Content", "Practice questions are original Kwado content unless labelled otherwise. Kwado AI is independent and not affiliated with JAMB, WAEC, NECO, NABTEB or any university."],
      ["AI tutor", "The AI tutor can make mistakes. Verified answer keys always take priority. Report any problem you find and our content team will review it."],
      ["Fair use", "Don't share accounts, scrape content, or use Kwado to cheat in a live examination."],
    ],
  },
};

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const doc = DOCS[slug];
  if (!doc) notFound();
  return (
    <div className="min-h-dvh bg-canvas">
      <header className="container flex h-16 items-center"><Logo /></header>
      <main className="container max-w-3xl pb-20 pt-6">
        <h1 className="text-3xl font-extrabold">{doc.title}</h1>
        <p className="mt-2 text-sm text-muted">Summary version. Last updated {new Date().getFullYear()}.</p>
        <div className="mt-8 space-y-6">
          {doc.sections.map(([h, b]) => (
            <section key={h} className="card p-6"><h2 className="font-bold">{h}</h2><p className="mt-2 text-[15px] text-muted">{b}</p></section>
          ))}
        </div>
        <Link href="/" className="mt-8 inline-block font-semibold text-brand-700">← Back home</Link>
      </main>
    </div>
  );
}
