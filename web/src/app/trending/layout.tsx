import type { Metadata } from "next";
import { social } from "@/lib/seo";

const title = "Stories developing over days";
const description = "The stories moving across Indian outlets right now, with the related coverage of each: how many outlets report it and who said what — counted, never implied.";
export const metadata: Metadata = {
  // A template, not a bare string: a string title here stopped the root's
  // "%s | Prism" reaching /trending/<slug>, whose titles then dropped the brand (audit 02, A6 / P2-3).
  title: { default: title, template: "%s | Prism" },
  description,
  alternates: { canonical: "/trending" },
  ...social(title, description, "/trending"),
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
