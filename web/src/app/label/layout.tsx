import type { Metadata } from "next";

// The labeller workspace and every batch under it: a tool, not a page. Kept out
// of the index here as well as in robots.ts, because a disallowed URL can still
// be indexed from a link; noindex is what keeps it out.
export const metadata: Metadata = {
  title: "Label for Prism",
  robots: { index: false, follow: false },
};

export default function LabelLayout({ children }: { children: React.ReactNode }) {
  return children;
}
