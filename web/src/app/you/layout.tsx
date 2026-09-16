import type { Metadata } from "next";

export const metadata: Metadata = { title: "Your chart", description: "Where you are, what you do, what you follow: how the chart is re-sorted for you." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
