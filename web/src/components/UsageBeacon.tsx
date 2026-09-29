"use client";

// One page view per route change, and one arrival per tab: where this visit
// came from (the referrer's host, never its path) or which Share button sent
// it (the `?s=` marker a shared link carries). /admin is never counted — the
// founders reading their own dashboard are not usage. Also, per tab: the 2nd
// and 5th story read (does a visit go past one story?), and any click on an
// element marked `data-cta` — the landing's buttons, which are server-rendered
// and cannot hold a handler (the API keeps only the words on its list).

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { pageKind, send } from "@/lib/analytics";

const ARRIVED = "prism.arrived";
const DEPTH = "prism.depth";
const DEPTHS = new Set([2, 5]); // common/usage.DEPTHS

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
    const kind = pageKind(pathname);
    send("view", kind);
    if (kind !== "story") return;
    try {
      const n = Number(sessionStorage.getItem(DEPTH) ?? 0) + 1;
      sessionStorage.setItem(DEPTH, String(n));
      if (DEPTHS.has(n)) send("depth", String(n));
    } catch {
      /* storage blocked: depth goes uncounted */
    }
  }, [pathname]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const cta = e.target instanceof Element ? e.target.closest("[data-cta]")?.getAttribute("data-cta") : null;
      if (cta) send("cta", cta);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);
  return null;
}
