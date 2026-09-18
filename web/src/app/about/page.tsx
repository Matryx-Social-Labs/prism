import type { Metadata } from "next";
import { Landing } from "@/components/Landing";

// The pitch at its permanent address. `/` shows the same page to a first
// visitor and sends everyone else to the chart (D5 revised), so the chart's
// promise line and the footer need somewhere the whole page always lives.
// Rendered per request so the proofs are today's, not the build's.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "About",
  description: "How Prism builds one inspectable story record from monitored outlets, then lets readers re-read it through a professional lens.",
};

export default async function AboutPage() {
  return Landing();
}
