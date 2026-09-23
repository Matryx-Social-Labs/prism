"use client";

// One page view per route change, and one arrival per tab: where this visit
// came from (the referrer's host, never its path) or which Share button sent
// it (the `?s=` marker a shared link carries). /admin is never counted — the
// founders reading their own dashboard are not usage.

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { pageKind, send } from "@/lib/analytics";

const ARRIVED = "prism.arrived";

export function UsageBeacon() {
  const pathname = usePathname();
  useEffect(() => {
    if (!pathname || pathname.startsWith("/admin")) return;
    try {
      if (!sessionStorage.getItem(ARRIVED)) {
        sessionStorage.setItem(ARRIVED, "1");
        let ref = "";
        try {
          const from = new URL(document.referrer);
          if (from.host !== window.location.host) ref = from.hostname;
        } catch {
          /* no referrer */
        }
        send("arrival", "", { ref, s: new URLSearchParams(window.location.search).get("s") ?? "" });
      }
    } catch {
      /* storage blocked: the arrival goes uncounted, the view below still counts */
    }
    send("view", pageKind(pathname));
  }, [pathname]);
  return null;
}
