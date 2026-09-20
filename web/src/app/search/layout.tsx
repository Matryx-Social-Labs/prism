import type { Metadata } from "next";

// Internal search results are not pages to index (they would be a page per
// query, and thin); the records they link to are.
export const metadata: Metadata = {
  title: "Search",
  description: "Search Prism's live records by story, entity, ticker or CVE id.",
  robots: { index: false, follow: true },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
