import type { Metadata } from "next";

export const metadata: Metadata = { title: "Today's chart", description: "Today's most-corroborated stories, one row per story: the number at the left is how many outlets reported it." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
