"use client";

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
    if (nav?.share) {
      try {
        await nav.share({ title, url: absolute });
        return;
      } catch {
        /* user dismissed — fall through to copy */
      }
    }
    try {
      await nav?.clipboard?.writeText(absolute);
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
          : "inline-flex min-h-[36px] items-center gap-1.5 rounded-full border px-3.5 text-[13px] font-medium transition hover:opacity-80"
      }
      style={{ borderColor: "var(--line-strong)", color: "var(--ink)", background: "var(--bg-elevated)" }}
      aria-label="Share this story"
    >
      <span aria-hidden>↗</span>
      {copied ? "Link copied" : "Share"}
    </button>
  );
}
