import type { Metadata } from "next";
import { social } from "@/lib/seo";

const title = "Today's record: Indian news, one page per story";
const description = "Today's stories from monitored Indian outlets, one record per story: who reported it, what changed, who said what — every line sourced.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/feed" },
  ...social(title, description, "/feed"),
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
