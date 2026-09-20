import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Today's record",
  description: "Today's stories from monitored Indian and international outlets, one record per story: who reported it, what changed, who said what — every line sourced.",
  alternates: { canonical: "/feed" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
