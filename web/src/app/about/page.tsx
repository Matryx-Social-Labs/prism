import type { Metadata } from "next";
import { social } from "@/lib/seo";
import { HowItWorks } from "@/components/HowItWorks";

// "How Prism works": one live story followed through the product step by
// step (components/HowItWorks.tsx). `/` keeps the pitch (Landing) for a first
// visitor; this is the page the chart's "How Prism works →" and the footer
// point at. Refreshed each minute so the example is today's, not the build's —
// the record fetch's own clock. It was force-dynamic: a function run for every
// visit to the page the site's structured data names as its principles.
export const revalidate = 60;

const title = "How Prism works: one record per story";
const description = "How Prism turns reports from a public list of Indian outlets into one record per story: who covered it, verbatim quotes, the brief, and how to correct it.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/about" },
  ...social(title, description, "/about"),
};

export default async function AboutPage() {
  return HowItWorks();
}
