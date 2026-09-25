"use client";

import { ShareIcon } from "@/components/icons";

// Web Share API on mobile (native WhatsApp/Instagram sheet — the India growth
// path); copy-link fallback on desktop. Shares the shareable /trending/<slug> URL.
import { useState } from "react";

import { shareSurface, track } from "@/lib/analytics";

export function ShareButton({ url, title, fill, compact, label }: { url: string; title: string; fill?: boolean; compact?: boolean; /** What is shared, for screen readers; a compact button defaults to the quote it sits under. */ label?: string }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const nav = typeof navigator !== "undefined" ? navigator : undefined;
    const surface = shareSurface(url);
    // `?s=` marks the link as shared, so the visit it brings back is counted as
    // one even when a chat app strips the referrer (api/routes/beacon.py).
    // Pages set their canonical URL, so the marker never splits a page in search.
    const target = new URL(url, typeof window !== "undefined" ? window.location.origin : "https://readprism.news");
    target.searchParams.set("s", surface);
    const absolute = target.toString();
    // Native sheet (WhatsApp/Instagram/…) wherever the browser offers it. It is
    // secure-context-only: over plain http:// — a LAN IP in dev — navigator.share
    // is undefined and we fall back to copying the link.
    if (nav?.share) {
      try {
        // `text` too: most chat apps ignore `title` and paste only text+url, so
        // without it the headline is lost and the share is a naked link.
        await nav.share({ title, text: title, url: absolute });
        track("Share", { surface });
        return;
      } catch (err) {
        // Dismissing the sheet is a decision, not a failure — copying the link
        // behind their back (and flashing "Link copied") ignores it.
        if ((err as Error)?.name === "AbortError") return;
        /* anything else — fall through to copy */
      }
    }
    // Check clipboard exists before claiming success: `nav?.clipboard?.writeText()`
    // short-circuits to undefined when the API is absent (it's secure-context-only
    // too), and `await undefined` resolves happily — so the old code flashed
    // "Link copied" on http origins having copied nothing at all.
    if (!nav?.clipboard) return;
    try {
      await nav.clipboard.writeText(absolute);
      track("Share", { surface });
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard blocked — nothing to do */
    }
  }

  if (compact) {
    // A text link in a meta row (a quote card's foot): the same behaviour, no chrome.
    return (
      <button type="button" onClick={share} className="font-semibold hover:underline" style={{ color: "var(--ink-2)", textUnderlineOffset: 4 }} aria-label={label ?? "Share this quote"}>
        {copied ? "Link copied" : "Share"}
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={share}
      className={`p-btn p-btn--secondary ${fill ? "w-full" : "p-btn--sm"}`}
      aria-label={label ?? "Share this story"}
    >
      <ShareIcon size={16} />
      {copied ? "Link copied" : "Share"}
    </button>
  );
}
