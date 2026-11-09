import { MarketingNav } from "@/components/marketing/nav";
import { Hero } from "@/components/marketing/hero";
import {
  ExamStrip, Faq, FinalCta, Footer, Gamification, HowItWorks, InteractivePreview, Pricing, RoadmapPreview,
  SubjectCoverage, Testimonials, TutorShowcase,
} from "@/components/marketing/sections";

export default function Home() {
  return (
    <>
      <MarketingNav />
      <main>
        <Hero />
        <ExamStrip />
        <HowItWorks />
        <InteractivePreview />
        <TutorShowcase />
        <RoadmapPreview />
        <Gamification />
        <SubjectCoverage />
        <Pricing />
        <Testimonials />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
