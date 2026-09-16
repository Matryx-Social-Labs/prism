import type { Metadata } from "next";

export const metadata: Metadata = { title: "Search", description: "Search stories, people, tickers and CVE ids across every outlet Prism reads." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
