import type { Metadata } from "next";

export const metadata: Metadata = { title: "Set up your chart", description: "Three steps: where you are, what you do, what you follow." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
