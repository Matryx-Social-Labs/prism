"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Check } from "@/components/icons";
import { BackBar, InfoCard, InShortCard, OnThisPage } from "@/components/ui";
import { shortDate } from "@/lib/dateline";
import { CONTACT_EMAIL, LEGAL_DOCS, LEGAL_ENTITY, LEGAL_PARTNER, LEGAL_UPDATED, anchor, type Block, type LegalDoc } from "@/lib/legal";

const num = (i: number) => String(i + 1).padStart(2, "0");
const CHANGED = `${shortDate(LEGAL_UPDATED)} ${LEGAL_UPDATED.slice(0, 4)}`;

// A policy in the record's own shape (Claude Design · screens/Legal.jsx): on
// the desk a numbered "On this page" (the section in view marked) at 200px,
// the text at the 640 measure, and beside it the whole document in a few plain
// lines, who is behind it and the other policies. On the phone the sections
// are a numbered chip rail and "In short" sits above the text. Each section
// opens under a rule with its number and, where the text has one, its own
// one-sentence version. LAYOUT ONLY: every word comes from lib/legal.ts — the
// board's wording is a draft and the LLP supplies the text.
export function LegalPage({ doc }: { doc: LegalDoc }) {
  const others = LEGAL_DOCS.filter((d) => d.slug !== doc.slug);
  const ids = doc.sections.map((s) => anchor(s.heading));
  const [active, setActive] = useState(ids[0]);

  // The scroll spy: the section whose top has crossed the upper band of the viewport.
  useEffect(() => {
    const els = ids.map((id) => document.getElementById(id)).filter((el): el is HTMLElement => el != null);
    if (els.length === 0 || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-15% 0px -75% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc.slug]);

  // The phone's chip rail keeps the section in view in sight as the reader scrolls.
  const chipRail = useRef<HTMLElement>(null);
  useEffect(() => {
    const rail = chipRail.current;
    const chip = rail?.querySelector<HTMLElement>('[aria-current="true"]');
    if (!rail || !chip || rail.clientWidth === 0) return;
    rail.scrollTo({ left: rail.scrollLeft + chip.getBoundingClientRect().left - rail.getBoundingClientRect().left - 16 });
  }, [active]);

  const inShort = (
    <InShortCard>
      <ul className="grid gap-1.5">
        {doc.inShort.map((line) => (
          <li key={line} className="flex items-start gap-2">
            <span className="mt-[3px] shrink-0" aria-hidden><Check size={14} /></span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
    </InShortCard>
  );
  const who = (
    <InfoCard
      title="Who is behind it"
      rows={[
        ["LLP", LEGAL_ENTITY],
        ["Built with", LEGAL_PARTNER],
        ["Write to", <a key="w" href={`mailto:${CONTACT_EMAIL}`} className="p-link">{CONTACT_EMAIL}</a>],
        ["Changed", <time key="c" dateTime={LEGAL_UPDATED} className="p-mono" style={{ fontSize: 12 }}>{CHANGED}</time>],
      ]}
    />
  );
  const also = (
    <InfoCard
      title="Also"
      rows={[
        ...others.map((d) => ["", <Link key={d.slug} href={`/${d.slug}`} className="p-link">{d.title}</Link>] as const),
        ["", <Link key="plus" href="/plus" className="p-link">Plus and prices</Link>],
        ["", <Link key="about" href="/about" className="p-link">How Prism works</Link>],
      ]}
    />
  );

  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto max-w-[var(--shell)] px-[var(--gutter)] pb-20 pt-5 lg:grid lg:grid-cols-[200px_minmax(0,640px)] lg:justify-center lg:gap-x-12 lg:pt-11 xl:grid-cols-[200px_minmax(0,640px)_280px]">
        {/* ── On this page (desk) ─────────────────────────────────────── */}
        <div className="hidden lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:block lg:self-start">
          <OnThisPage items={doc.sections.map((s) => ({ id: anchor(s.heading), label: s.heading }))} current={active} />
        </div>

        {/* ── The document ───────────────────────────────────────────── */}
        <article className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-7">
          <header className="grid gap-2.5">
            <p className="p-meta">
              <span className="p-meta__subject">{doc.kind}</span>
              <span className="p-meta__sep" />
              <span className="p-meta__subject" style={{ fontWeight: 500 }}>Last changed</span>
              <time dateTime={LEGAL_UPDATED} className="p-meta__prov">{CHANGED}</time>
            </p>
            <h1 className="text-balance [font:var(--t-display-l)] lg:[font:var(--t-display-xl)]" style={{ letterSpacing: "var(--track-display)" }}>{doc.title}</h1>
            <p className="max-w-[62ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{doc.lede}</p>
          </header>

          {/* Phone: the sections as a numbered chip rail, and the short version first. */}
          <nav ref={chipRail} className="p-hide-scroll -mx-[var(--gutter)] flex gap-1.5 overflow-x-auto px-[var(--gutter)] lg:hidden" aria-label="Sections">
            {doc.sections.map((s, i) => {
              const id = anchor(s.heading);
              return (
                <a key={id} href={`#${id}`} className="p-chip" aria-current={active === id ? "true" : undefined}>
                  <span aria-hidden="true" className="p-mono" style={{ fontSize: 11 }}>{num(i)}</span>
                  {s.heading}
                </a>
              );
            })}
          </nav>
          <div className="xl:hidden">{inShort}</div>

          {doc.sections.map((s, i) => {
            const id = anchor(s.heading);
            return (
              <section
                key={id}
                id={id}
                className="grid scroll-mt-24 gap-2.5 pt-[22px]"
                style={{ borderTop: i ? "1px solid var(--line)" : "var(--rule-section) solid var(--ink)" }}
                aria-labelledby={`${id}-title`}
              >
                <h2 id={`${id}-title`} className="flex items-baseline gap-2.5 text-balance" style={{ font: "var(--t-display-m)" }}>
                  <span aria-hidden="true" className="p-mono shrink-0" style={{ fontSize: 12, color: "var(--ink-3)" }}>{num(i)}</span>
                  <span>{s.heading}</span>
                </h2>
                {s.short && (
                  <p className="grid grid-cols-[auto_minmax(0,1fr)] gap-2.5" style={{ font: "600 15px/1.5 var(--font-read)" }}>
                    <span className="p-eyebrow pt-0.5">In short</span>
                    <span>{s.short}</span>
                  </p>
                )}
                {s.blocks.map((b, j) => <BlockView key={j} block={b} />)}
              </section>
            );
          })}

          {/* Below the wide desk the rail's cards close the document. */}
          <div className="grid gap-3.5 xl:hidden">
            {who}
            {also}
          </div>
        </article>

        {/* ── Beside the document (wide desk) ────────────────────────── */}
        <aside className="hidden xl:sticky xl:top-[calc(var(--topbar)+24px)] xl:grid xl:content-start xl:gap-3.5 xl:self-start" aria-label="About this document">
          {inShort}
          {who}
          {also}
        </aside>
      </div>
    </>
  );
}

function BlockView({ block }: { block: Block }) {
  if (typeof block === "string") return <p className="max-w-[62ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{block}</p>;
  return (
    <ul className="grid max-w-[62ch] gap-1.5" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
      {block.map((li) => (
        <li key={li} className="flex items-start gap-2.5">
          <span className="mt-[11px] h-[3px] w-[3px] shrink-0 rounded-full" style={{ background: "var(--ink-3)" }} aria-hidden />
          <span>{li}</span>
        </li>
      ))}
    </ul>
  );
}
