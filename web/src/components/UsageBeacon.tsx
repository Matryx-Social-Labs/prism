"use client";

// One page view per route change, and one arrival per tab: where this visit
// came from (the referrer's host, never its path) or which Share button sent
// it (the `?s=` marker a shared link carries), plus the campaign word its link
// carried (`?ref=`, lib/attribution). /admin is never counted — the
// founders reading their own dashboard are not usage. Also, per tab: the 2nd
// and 5th story read (does a visit go past one story?), and any click on an
// element marked `data-cta` — the landing's buttons, which are server-rendered
// and cannot hold a handler (the API keeps only the words on its list).

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { pageKind, send } from "@/lib/analytics";
import { campaignWord, isShareMarker, withoutCampaign } from "@/lib/attribution";

// "share" when the visit arrived by a shared link, so its 2nd story also
// counts as `depth:2:share` (the share loop, 06 §2.2b); "1" otherwise.
const ARRIVED = "prism.arrived";
const DEPTH = "prism.depth";
const DEPTHS = new Set([2, 5]); // common/usage.DEPTHS

export function UsageBeacon() {
  const pathname = usePathname();
  useEffect(() => {
    if (!pathname || pathname.startsWith("/admin")) return;
    try {
      if (!sessionStorage.getItem(ARRIVED)) {
        const params = new URLSearchParams(window.location.search);
        const s = params.get("s") ?? "";
        sessionStorage.setItem(ARRIVED, isShareMarker(s) ? "share" : "1");
        let ref = "";
        try {
          const from = new URL(document.referrer);
          if (from.host !== window.location.host) ref = from.hostname;
        } catch {
          /* no referrer */
        }
        send("arrival", "", { ref, s });
        const campaign = campaignWord(params);
        if (campaign) send("campaign", campaign);
      }
    } catch {
      /* storage blocked: the arrival goes uncounted, the view below still counts */
    }
    // Counted (or not) above; either way the word leaves the address bar, so a
    // link copied from here does not credit the campaign twice.
    try {
      const clean = withoutCampaign(window.location.href);
      if (clean) window.history.replaceState(window.history.state, "", clean);
    } catch {
      /* history blocked: the address keeps its word, nothing else changes */
    }
    const kind = pageKind(pathname);
    send("view", kind);
    if (kind !== "story") return;
    try {
      const n = Number(sessionStorage.getItem(DEPTH) ?? 0) + 1;
      sessionStorage.setItem(DEPTH, String(n));
      if (DEPTHS.has(n)) send("depth", String(n));
      if (n === 2 && sessionStorage.getItem(ARRIVED) === "share") send("depth", "2:share");
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
