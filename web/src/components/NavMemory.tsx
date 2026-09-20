"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { notePath } from "@/lib/nav";

/** Notes each client navigation so a back bar can tell "came from inside" (lib/nav.ts). */
export function NavMemory() {
  const pathname = usePathname();
  useEffect(() => {
    if (pathname) notePath(pathname);
  }, [pathname]);
  return null;
}
