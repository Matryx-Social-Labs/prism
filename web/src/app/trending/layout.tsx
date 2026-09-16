import type { Metadata } from "next";

export const metadata: Metadata = { title: "Trending", description: "The stories that are moving: developments, branches and outlets, counted." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
