import type { Metadata } from "next";

export const metadata: Metadata = { title: "Sign in", description: "A one-time link to your email, no password." };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
