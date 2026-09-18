"use client";

import { ArrowUpRight } from "@/components/icons";

// Web Share API on mobile (native WhatsApp/Instagram sheet — the India growth
// path); copy-link fallback on desktop. Shares the shareable /trending/<slug> URL.
import { useState } from "react";

export function ShareButton({ url, title, fill }: { url: string; title: string; fill?: boolean }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const nav = typeof navigator !== "undefined" ? navigator : undefined;
    const absolute = url.startsWith("http")
      ? url
      : `${typeof window !== "undefined" ? window.location.origin : ""}${url}`;
    // Native sheet (WhatsApp/Instagram/…) wherever the browser offers it. It is
    // secure-context-only: over plain http:// — a LAN IP in dev — navigator.share
    // is undefined and we fall back to copying the link.
    if (nav?.share) {
      try {
        // `text` too: most chat apps ignore `title` and paste only text+url, so
        // without it the headline is lost and the share is a naked link.
        await nav.share({ title, text: title, url: absolute });
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
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard blocked — nothing to do */
    }
  }

  return (
    <button
      type="button"
      onClick={share}
      className={
        fill
          ? "flex h-11 w-full items-center justify-center gap-1.5 rounded-full border text-[13.5px] font-semibold transition hover:opacity-80"
          : "inline-flex h-11 items-center gap-1.5 border px-3 text-[13px] font-medium transition hover:opacity-80"
      }
      style={{ borderColor: "var(--line-strong)", color: "var(--ink)", background: fill ? "var(--bg-elevated)" : "transparent" }}
      aria-label="Share this story"
    >
      <ArrowUpRight />
      {copied ? "Link copied" : "Share"}
    </button>
  );
}
