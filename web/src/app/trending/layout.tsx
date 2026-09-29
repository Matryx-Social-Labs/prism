import type { Metadata } from "next";
import { social } from "@/lib/seo";

const title = "Stories developing over days";
const description = "The stories moving across Indian outlets right now, with the related coverage of each: how many outlets report it and who said what — counted, never implied.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/trending" },
  ...social(title, description, "/trending"),
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
