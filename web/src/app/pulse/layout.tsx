import type { Metadata } from "next";

// Not indexed while it renders in the browser: a crawler gets 26 words and an
// empty shell (crawl of 2026-09-27). It stays readable and linkable.
export const metadata: Metadata = {
  title: "Market pulse",
  description: "The day's markets read, written from the stories on the chart.",
  alternates: { canonical: "/pulse" },
  robots: { index: false, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
