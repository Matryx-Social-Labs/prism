import type { Metadata } from "next";

export const metadata: Metadata = { title: "Watchlist", description: "The stories that touch the tickers and sectors you follow." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
