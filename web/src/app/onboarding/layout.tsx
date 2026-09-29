import type { Metadata } from "next";

export const metadata: Metadata = { title: "Set up your feed", description: "Three steps, all optional: where you are, what you do, what you follow." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
