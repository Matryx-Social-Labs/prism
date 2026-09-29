import type { Metadata } from "next";
import { social } from "@/lib/seo";

const title = "Today's record: Indian news, one page per story";
const description = "Today's stories from monitored Indian outlets, one record per story: who reported it, what changed, who said what — every line sourced.";
export const metadata: Metadata = {
  // A template, not a bare string: a string title here stopped the root's
  // "%s | Prism" reaching /feed/<date> (the day archive), whose titles then dropped the brand (audit 02, A6 / P2-3).
  title: { default: title, template: "%s | Prism" },
  description,
  alternates: { canonical: "/feed" },
  ...social(title, description, "/feed"),
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
