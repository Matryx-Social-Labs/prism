import type { Metadata } from "next";
import { social } from "@/lib/seo";

// Not indexed while it renders in the browser: a crawler gets 26 words and an
// empty shell (crawl of 2026-09-27). It stays readable and linkable.
const title = "Market pulse";
const description = "The listed companies and market-wide forces the last 24 hours of Indian business reporting named, most-reported first.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/pulse" },
  robots: { index: false, follow: true },
  ...social(title, description, "/pulse"),
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
