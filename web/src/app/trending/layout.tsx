import type { Metadata } from "next";

export const metadata: Metadata = { title: "Trending", description: "The coverage moving now: related events and reporting outlets, counted without implying an unverified chronology." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
