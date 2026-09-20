import type { Metadata } from "next";
import { HowItWorks } from "@/components/HowItWorks";

// "How Prism works": one live story followed through the product step by
// step (components/HowItWorks.tsx). `/` keeps the pitch (Landing) for a first
// visitor; this is the page the chart's "How Prism works →" and the footer
// point at. Rendered per request so the example is today's, not the build's.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "How Prism works",
  description: "One story from today's record, followed through Prism step by step: the reports, the record, who covered it, who said what, the brief, the lens, the question box.",
  alternates: { canonical: "/about" },
};

export default async function AboutPage() {
  return HowItWorks();
}
