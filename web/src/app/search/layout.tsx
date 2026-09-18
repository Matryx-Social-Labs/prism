import type { Metadata } from "next";

export const metadata: Metadata = { title: "Search", description: "Search Prism's live records by story, entity, ticker or CVE id." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
