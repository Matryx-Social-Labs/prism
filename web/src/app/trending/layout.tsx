import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Stories developing over days",
  description: "The stories moving across Indian outlets right now, with the related coverage of each: how many outlets report it and who said what — counted, never implied.",
  alternates: { canonical: "/trending" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
