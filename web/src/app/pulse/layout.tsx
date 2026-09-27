import type { Metadata } from "next";

// Not indexed while it renders in the browser: a crawler gets 26 words and an
// empty shell (crawl of 2026-09-27). It stays readable and linkable.
export const metadata: Metadata = {
  title: "Market pulse",
  description: "The listed companies and market-wide forces the last 24 hours of Indian business reporting named, most-reported first.",
  alternates: { canonical: "/pulse" },
  robots: { index: false, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
