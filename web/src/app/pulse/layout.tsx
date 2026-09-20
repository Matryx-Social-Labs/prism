import type { Metadata } from "next";

export const metadata: Metadata = { title: "Market pulse", description: "The day's markets read, written from the stories on the chart.", alternates: { canonical: "/pulse" } };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
