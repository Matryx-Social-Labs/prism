"use client";

import Image from "next/image";
import Link from "next/link";
import type { FeedItem } from "@/lib/api";
import { detectScript, langName, langNative } from "@/lib/languages";

export function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function itemMeta(item: FeedItem): string {
  return `${item.source_count} source${item.source_count === 1 ? "" : "s"} · ${timeAgo(item.last_updated_at)}`;
}

export function StoryBadges({ item, lens, primaryLang = "en" }: { item: FeedItem; lens: string; primaryLang?: string }) {
  const chip = "rounded-full px-[9px] py-0.5 text-[11px] font-semibold whitespace-nowrap";
  // Tag the headline's language only when it isn't the reader's primary — so a
  // Hindi/Kannada headline reads as "translation available" rather than a
  // surprise (design v3). Bordered + UI font (a locale tag, not provenance).
  // Fall back to script detection when the API doesn't tag the language.
  const headlineLang = item.headline_lang ?? detectScript(item.title);
  const showLang = headlineLang && headlineLang !== primaryLang;
  return (
    <>
      {showLang && (
        <span
          className={`${chip} border`}
          style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
          title={`Headline is in ${langName(headlineLang)}${item.available_languages.includes(primaryLang) ? " — translation available" : ""}`}
        >
          {langNative(headlineLang)}
        </span>
      )}
      {item.sector && (
        <span
          className={`${chip} uppercase tracking-wide`}
          style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)", fontSize: "10.5px" }}
        >
          {item.subsector ? item.subsector.replaceAll("_", " ") : item.sector}
        </span>
      )}
      {item.coverage?.single_origin && (
        <span
          className={chip}
          style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
          title="Only one country's outlets have covered this so far"
        >
          ⚠ Single-origin
        </span>
      )}
      {item.is_regional && (
        <span className={chip} style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
          ◉ Your region
        </span>
      )}
      {item.cvss_score != null && (
        <span className={chip} style={{ background: "var(--danger-bg)", color: "var(--danger)" }}>
          CVSS {item.cvss_score.toFixed(1)}
        </span>
      )}
      {item.kev_listed && (
        <span className={chip} style={{ background: "var(--danger)", color: "#fff" }}>
          ⚠ Actively exploited
        </span>
      )}
      {item.cve_ids.slice(0, 2).map((cve) => (
        <span key={cve} className="rounded-full px-[9px] py-0.5 font-mono text-[11px]" style={{ background: "var(--bg-sunken)" }}>
          {cve}
        </span>
      ))}
      {item.tickers.slice(0, 3).map((t) => (
        <span key={t} className="rounded-full px-[9px] py-0.5 font-mono text-[11px] font-semibold" style={{ background: "var(--lens-finance-bg)", color: "var(--lens-finance)" }}>
          ${t}
        </span>
      ))}
      {item.catalyst && (
        // Catalyst type — a provenance/evidence label (IBM Plex Mono, DESIGN.md).
        // Monochrome by default; takes the markets hue only when the finance
        // lens is speaking (color-means-lens). Never a per-catalyst palette.
        <span
          className="rounded-full border px-[8px] py-px font-mono text-[10px] font-medium uppercase tracking-wide"
          style={
            lens === "markets"
              ? { borderColor: "var(--lens-finance)", color: "var(--lens-finance)" }
              : { borderColor: "var(--line-strong)", color: "var(--ink-muted)" }
          }
          title="Catalyst type — what is moving this story"
        >
          {item.catalyst.replaceAll("_", " ")}
        </span>
      )}
      {item.price_impact_direction && (
        <span
          className={chip}
          style={
            item.price_impact_direction === "up"
              ? { background: "var(--up-bg)", color: "var(--up)" }
              : item.price_impact_direction === "down"
                ? { background: "var(--danger-bg)", color: "var(--danger)" }
                : { background: "var(--bg-sunken)", color: "var(--ink-muted)" }
          }
        >
          {item.price_impact_direction === "up" ? "▲" : item.price_impact_direction === "down" ? "▼" : "◆"} price
        </span>
      )}
    </>
  );
}

export function StoryRowCard({ item, lens, primaryLang }: { item: FeedItem; lens: string; primaryLang?: string }) {
  return (
    <Link
      href={`/story/${item.id}`}
      className="card-hover flex items-start gap-4 rounded-[18px] border px-5 py-[18px]"
      style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
    >
      <span className="flex min-w-0 flex-1 flex-col gap-2">
        <span className="flex flex-wrap items-center gap-[5px]">
          <StoryBadges item={item} lens={lens} primaryLang={primaryLang} />
          <span className="ml-auto font-mono text-[10.5px]" style={{ color: "var(--ink-muted)" }}>
            {itemMeta(item)}
          </span>
        </span>
        <span className="text-[15.5px] font-semibold leading-[1.4]" style={{ color: "var(--ink)" }}>
          {item.title}
        </span>
        {item.summary && (
          <span className="line-clamp-2 text-[13px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>
            {item.summary}
          </span>
        )}
      </span>
      {item.image_url && (
        <span className="relative hidden h-[92px] w-[92px] shrink-0 overflow-hidden rounded-xl sm:block" style={{ background: "var(--bg-sunken)" }}>
          <Image
            src={item.image_url}
            alt=""
            fill
            sizes="92px"
            className="object-cover"
            onError={(e) => {
              (e.currentTarget.parentElement as HTMLElement).style.display = "none";
            }}
          />
        </span>
      )}
    </Link>
  );
}

export function TopStoryCard({ item, lens, primaryLang }: { item: FeedItem; lens: string; primaryLang?: string }) {
  return (
    <Link
      href={`/story/${item.id}`}
      className="card-hover flex flex-col overflow-hidden rounded-[18px] border"
      style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
    >
      {item.image_url && (
        <span className="relative block h-[120px]" style={{ background: "var(--bg-sunken)" }}>
          <Image
            src={item.image_url}
            alt=""
            fill
            sizes="(max-width: 880px) 100vw, 340px"
            className="object-cover"
            onError={(e) => {
              (e.currentTarget.parentElement as HTMLElement).style.display = "none";
            }}
          />
        </span>
      )}
      <span className="flex flex-1 flex-col gap-[9px] px-[18px] pb-[18px] pt-4">
        <span className="flex flex-wrap gap-[5px]">
          <StoryBadges item={item} lens={lens} primaryLang={primaryLang} />
        </span>
        <span className="text-[15.5px] font-semibold leading-[1.4]" style={{ color: "var(--ink)" }}>
          {item.title}
        </span>
        {item.summary && (
          <span className="line-clamp-2 text-[13px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>
            {item.summary}
          </span>
        )}
        <span className="mt-auto font-mono text-[10.5px]" style={{ color: "var(--ink-muted)" }}>
          {itemMeta(item)}
        </span>
      </span>
    </Link>
  );
}
