import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Stories developing over days",
  description: "The stories moving across Indian and international outlets right now: how many report each one, how it unfolded, and who said what — counted, never implied.",
  alternates: { canonical: "/trending" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
