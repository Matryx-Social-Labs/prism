import type { Metadata } from "next";

import { AdminShell } from "@/components/admin/AdminShell";

// A tool, not a page: kept out of the index here as well as in robots.ts,
// because a disallowed URL can still be indexed from a link.
export const metadata: Metadata = {
  title: "Prism admin",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
