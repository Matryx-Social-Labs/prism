"use client";

import Image from "next/image";
import Link from "next/link";

import type { FeedItem } from "@/lib/api";
import {
  bandOrigins,
  bands,
  istDate,
  istTime,
  lastMoved,
  origins,
  sectorEyebrow,
} from "@/lib/dateline";
import { CARD_W, thumbUrl } from "@/lib/thumb";

// The desktop Feed (Parse Desktop.dc.html, FEED screen).
//
// Desktop was the mobile column widened: one ranked list, 620px of content and
// 400px of dead ivory each side. This is the composition the design actually
// calls for — a lead, an "also reading this" rail beside it, then sector bands —
// on The Stone grid: a 104px mono ledger rail outside a 1240px field of twelve
// 74px columns with 32px gutters (104 + 32 + 1240 = 1376).
//
// The rail is the point. Every provenance claim — source count, the newsroom
// clock, which countries filed — lives in the left margin in mono, so the prose
// column is never interrupted by chips. Nothing in the field states a fact about
// where a story came from.

const RAIL = "grid grid-cols-[104px_1240px] gap-x-8";
const FIELD = "grid grid-cols-[repeat(12,74px)] gap-x-8";
const MONO = "font-mono text-[10.5px] uppercase tracking-[0.1em]";

function Rail({ children }: { children: React.ReactNode }) {
  return <div className={`${MONO} leading-[1.9]`} style={{ color: "var(--ink-faint)" }}>{children}</div>;
}

function Meta({ item }: { item: FeedItem }) {
  const o = origins(item, 2);
  return (
    <div className={`${MONO} mt-2.5`} style={{ color: "var(--ink-faint)" }}>
      {[`${item.source_count} source${item.source_count === 1 ? "" : "s"}`, istTime(item.last_updated_at), o]
        .filter(Boolean)
        .join(" · ")}
    </div>
  );
}

export function FeedDesktop({ items, top }: { items: FeedItem[]; top: FeedItem[] }) {
  const lead = top[0] ?? items[0];
  if (!lead) return null;

  // The four beside the lead: highest-ranked, never repeating the lead.
  const also = [...top.slice(1), ...items].filter((i) => i.id !== lead.id).slice(0, 4);
  const used = new Set([lead.id, ...also.map((i) => i.id)]);
  // A sector with a single story got its own full-width row: one 160px photo and
  // three empty columns, which reads as a failed load rather than a thin sector.
  // On a live feed that was three of six rows. They collapse into one "Also
  // filed" band instead — every sector still appears, in a quarter of the space.
  const all = bands(items, used);
  const sectorBands = all.filter((b) => b.items.length > 1);
  const singles = all.filter((b) => b.items.length === 1);

  const totalSources = items.reduce((n, i) => n + (i.source_count || 0), 0);

  return (
    <div className="mx-auto hidden w-[1376px] pb-20 lg:block">
      {/* Dateline — the newsroom's own header line. */}
      <div className={`${RAIL} pt-5`}>
        <div />
        <div
          className={`${MONO} border-b pb-[18px]`}
          style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
        >
          {[
            istDate(new Date()),
            `${istTime(new Date().toISOString())} IST`,
            `${totalSources.toLocaleString("en-IN")} SOURCES`,
            `${items.length} STORIES`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </div>
      </div>

      {/* Lead + also reading */}
      <div className={`${RAIL} pt-7`}>
        <Rail>
          <div style={{ color: "var(--ink-muted)" }}>
            {lead.source_count} source{lead.source_count === 1 ? "" : "s"}
          </div>
          <div>{istTime(lead.last_updated_at)} IST</div>
          <div>{origins(lead)}</div>
          <div className="mt-3">LEAD</div>
          {lead.coverage?.single_origin && <div style={{ color: "var(--danger)" }}>SINGLE-ORIGIN</div>}
        </Rail>

        <div className={FIELD}>
          <article style={{ gridColumn: "1 / span 7" }}>
            <Link href={`/story/${lead.id}`} className="block">
              <div
                className="relative h-[400px] w-full overflow-hidden"
                style={{ background: "var(--bg-sunken)" }}
              >
                {lead.image_url && (
                  <Image
                    src={thumbUrl(lead.image_url, 1200)}
                    alt=""
                    fill
                    sizes="710px"
                    priority
                    className="object-cover"
                    onError={(e) => {
                      (e.currentTarget.parentElement as HTMLElement).style.display = "none";
                    }}
                  />
                )}
              </div>
              <div className={`${MONO} mt-[18px]`} style={{ color: "var(--ink-muted)" }}>
                {sectorEyebrow(lead)}
              </div>
              <h1
                className="mt-2.5 text-[42px] font-semibold leading-[1.12]"
                style={{ fontFamily: "var(--font-display), serif", textWrap: "pretty" }}
              >
                {lead.title}
              </h1>
            </Link>
            {lead.summary && (
              <p
                className="mt-3.5 max-w-[604px] text-[14.5px] leading-[1.6]"
                style={{ color: "var(--ink-muted)", textWrap: "pretty" }}
              >
                {lead.summary}
              </p>
            )}
          </article>

          <aside style={{ gridColumn: "9 / span 4" }}>
            <div
              className={`${MONO} border-b pb-3`}
              style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
            >
              Also reading this
            </div>
            <div className="flex flex-col">
              {also.map((i, n) => (
                <Link
                  key={i.id}
                  href={`/story/${i.id}`}
                  className="py-4 text-[15.5px] leading-[1.35] transition hover:opacity-70"
                  style={{
                    borderBottom: n < also.length - 1 ? "1px solid var(--line)" : undefined,
                    textWrap: "pretty",
                  }}
                >
                  {i.title}
                </Link>
              ))}
            </div>
          </aside>
        </div>
      </div>

      {/* Sector bands — four across, the first carrying the image. */}
      {sectorBands.map((band) => (
        <section key={band.sector} className={`${RAIL} mt-14 border-t pt-6`} style={{ borderColor: "var(--line)" }}>
          <Rail>
            <div>
              {band.items.length} stor{band.items.length === 1 ? "y" : "ies"}
            </div>
            <div>last moved {lastMoved(band.items)}</div>
            <div>{bandOrigins(band.items)}</div>
            {/* No SINGLE-ORIGIN flag here. It was some(), which on an India-only
                feed was true for five bands out of six — a warning that fires on
                nearly everything reports nothing. It stays on the lead, where it
                describes one story rather than a set. */}
          </Rail>

          <div>
            <div className="mb-[18px] flex items-baseline gap-3">
              <h2 className="text-[12px] font-semibold capitalize" style={{ color: "var(--ink-muted)" }}>
                {band.sector.replaceAll("_", " ")}
              </h2>
              {/* Depth lives on the sector page, not in a horizontal scroller:
                  the desktop design has no overflow-x anywhere, and the mobile
                  feed already sends readers here for the rest of a sector. */}
              {band.total > band.items.length && (
                <Link
                  href={`/sector/${band.sector}`}
                  className={`${MONO} transition hover:opacity-70`}
                  style={{ color: "var(--ink-faint)" }}
                >
                  All {band.total} →
                </Link>
              )}
            </div>
            <div className={FIELD}>
              {band.items.map((i, n) => (
                <article
                  key={i.id}
                  style={{
                    gridColumn: `${1 + n * 3} / span 3`,
                    // The first column carries the image; the rest are separated
                    // by a hairline instead, so the row reads as one band.
                    borderLeft: n > 0 ? "1px solid var(--line)" : undefined,
                    paddingLeft: n > 0 ? 24 : undefined,
                  }}
                >
                  {n === 0 && (
                    <div
                      className="relative mb-3.5 h-[160px] w-full overflow-hidden"
                      style={{ background: "var(--bg-sunken)" }}
                    >
                      {i.image_url && (
                        <Image
                          src={thumbUrl(i.image_url, CARD_W)}
                          alt=""
                          fill
                          sizes="248px"
                          className="object-cover"
                          onError={(e) => {
                            (e.currentTarget.parentElement as HTMLElement).style.display = "none";
                          }}
                        />
                      )}
                    </div>
                  )}
                  <Link
                    href={`/story/${i.id}`}
                    className="block text-[15.5px] leading-[1.35] transition hover:opacity-70"
                    style={{ textWrap: "pretty" }}
                  >
                    {i.title}
                  </Link>
                  <Meta item={i} />
                </article>
              ))}
            </div>
          </div>
        </section>
      ))}

      {/* The thin sectors, four across, each still under its own name. */}
      {singles.length > 0 && (
        <section className={`${RAIL} mt-14 border-t pt-6`} style={{ borderColor: "var(--line)" }}>
          <Rail>
            <div>{singles.length} sectors</div>
            <div>last moved {lastMoved(singles.flatMap((b) => b.items))}</div>
            <div>{bandOrigins(singles.flatMap((b) => b.items))}</div>
          </Rail>
          <div>
            <h2 className="mb-[18px] text-[12px] font-semibold" style={{ color: "var(--ink-muted)" }}>
              Also filed
            </h2>
            <div className={`${FIELD} gap-y-7`}>
              {singles.map((band, n) => (
                <article
                  key={band.sector}
                  style={{
                    gridColumn: "span 3",
                    borderLeft: n % 4 > 0 ? "1px solid var(--line)" : undefined,
                    paddingLeft: n % 4 > 0 ? 24 : undefined,
                  }}
                >
                  <Link
                    href={`/sector/${band.sector}`}
                    className={`${MONO} mb-2 block capitalize transition hover:opacity-70`}
                    style={{ color: "var(--ink-faint)" }}
                  >
                    {band.sector.replaceAll("_", " ")}
                  </Link>
                  <Link
                    href={`/story/${band.items[0].id}`}
                    className="block text-[15.5px] leading-[1.35] transition hover:opacity-70"
                    style={{ textWrap: "pretty" }}
                  >
                    {band.items[0].title}
                  </Link>
                  <Meta item={band.items[0]} />
                </article>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

