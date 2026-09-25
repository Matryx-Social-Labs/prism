"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Check } from "@/components/icons";
import { CONTACT_EMAIL, LEGAL_DOCS, LEGAL_ENTITY, LEGAL_UPDATED, anchor, type Block, type LegalDoc } from "@/lib/legal";

// A policy in the record's own shape (DESIGN.md § Legal pages): the story
// page's three columns — "On this page" in the left rail with the section
// you are reading marked, the text at the reading measure, and in the right
// rail the whole document in a few plain lines ("In short"), when it last
// changed, who is behind it, and the other policies. Each section opens with
// its one-sentence version, so a reader who will not read the paragraphs
// still leaves knowing the rule. On the phone the sections become a chip
// rail under the title and "In short" sits above the text. No cards in the
// column, hairlines between sections, mono for dates and labels.
export function LegalPage({ doc }: { doc: LegalDoc }) {
  const others = LEGAL_DOCS.filter((d) => d.slug !== doc.slug);
  const ids = doc.sections.map((s) => anchor(s.heading));
  const [active, setActive] = useState(ids[0]);

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

  const inShort = (
    <div className="card">
      <h2 className="card-h">In short</h2>
      <ul className="flex flex-col gap-2 text-[14px] leading-[1.5]">
        {doc.inShort.map((line) => (
          <li key={line} className="flex items-start gap-2">
            <span className="mt-[3px] shrink-0" aria-hidden><Check size={14} /></span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="mx-auto max-w-[var(--shell)] px-5 pb-20 pt-6 sm:px-8 lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-x-8 lg:pt-10 xl:grid-cols-[var(--rail)_minmax(0,1fr)_var(--evidence)] xl:gap-x-10 xl:px-10">
      {/* ── On this page (desk) ─────────────────────────────────────── */}
      <aside className="hidden lg:block lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start" aria-label="On this page">
        <p className="mb-2 text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>On this page</p>
        <ol>
          {doc.sections.map((s, i) => {
            const id = anchor(s.heading);
            const on = active === id;
            return (
              <li key={id} className={i > 0 ? "border-t" : ""} style={i > 0 ? { borderColor: "var(--line)" } : undefined}>
                <a href={`#${id}`} aria-current={on ? "true" : undefined} className="flex items-center justify-between py-2.5 text-[14px] underline-offset-4 hover:underline" style={{ color: on ? "var(--accent)" : "var(--ink-2)", fontWeight: on ? 600 : 500 }}>
                  {s.heading}
                </a>
              </li>
            );
          })}
        </ol>
      </aside>

      {/* ── The document ───────────────────────────────────────────── */}
      <article className="min-w-0 lg:max-w-[var(--reading)]">
        <header>
          <p className="meta-line">
            <span>{doc.kind}</span>
            <span className="dot" />
            <span>Last changed <time dateTime={LEGAL_UPDATED}>{LEGAL_UPDATED}</time></span>
          </p>
          <h1 className="font-record mt-2 text-[34px] font-bold leading-[1.2] text-balance sm:text-[40px]">{doc.title}</h1>
          <p className="mt-4 text-[16.5px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>{doc.lede}</p>
        </header>

        {/* Phone: the sections as a chip rail, and the short version first. */}
        <nav className="hide-scroll -mx-5 mt-5 flex gap-2 overflow-x-auto px-5 lg:hidden" aria-label="Sections">
          {doc.sections.map((s) => (
            <a key={s.heading} href={`#${anchor(s.heading)}`} className="chip h-8 shrink-0 px-3 text-[13px]">{s.heading}</a>
          ))}
        </nav>
        <div className="mt-5 xl:hidden">{inShort}</div>

        {doc.sections.map((s) => {
          const id = anchor(s.heading);
          return (
            <section key={id} id={id} className="scroll-mt-24 mt-8 border-t pt-5" style={{ borderColor: "var(--line)" }} aria-labelledby={`${id}-title`}>
              <h2 id={`${id}-title`} className="font-record text-[24px] font-bold leading-[1.2] tracking-[-0.01em]">{s.heading}</h2>
              {s.short && (
                <p className="mt-1.5 text-[15px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
                  <span className="p-eyebrow mr-2">In short</span>
                  {s.short}
                </p>
              )}
              {s.blocks.map((b, i) => <BlockView key={i} block={b} />)}
            </section>
          );
        })}

        <nav aria-label="Other policies" className="mt-12 flex flex-wrap gap-x-5 gap-y-2 border-t pt-5 text-[14px] font-medium" style={{ borderColor: "var(--line)" }}>
          {others.map((d) => (
            <Link key={d.slug} href={`/${d.slug}`} className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>
              {d.title} →
            </Link>
          ))}
        </nav>
      </article>

      {/* ── Beside the document (wide desk) ────────────────────────── */}
      <aside className="hidden xl:flex xl:flex-col xl:gap-4 xl:sticky xl:top-[calc(var(--topbar)+24px)] xl:self-start" aria-label="About this document">
        {inShort}
        <div className="card">
          <h2 className="card-h">Who is behind it</h2>
          <p className="text-[14px] leading-[1.5]">{LEGAL_ENTITY}</p>
          <p className="mt-1 font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{CONTACT_EMAIL}</p>
          <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Last changed {LEGAL_UPDATED}</p>
        </div>
        <div className="card">
          <h2 className="card-h">Also</h2>
          <ul className="flex flex-col gap-1.5 text-[14px]">
            {others.map((d) => (
              <li key={d.slug}><Link href={`/${d.slug}`} className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>{d.title} →</Link></li>
            ))}
            <li><Link href="/plus" className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>Plus and prices →</Link></li>
          </ul>
        </div>
      </aside>
    </div>
  );
}

function BlockView({ block }: { block: Block }) {
  if (typeof block === "string") return <p className="mt-3 text-[16px] leading-[1.65]">{block}</p>;
  return (
    <ul className="mt-3 flex flex-col gap-1.5 text-[16px] leading-[1.6]">
      {block.map((li) => (
        <li key={li} className="flex items-start gap-2.5">
          <span className="mt-[11px] h-[3px] w-[3px] shrink-0 rounded-full" style={{ background: "var(--ink-3)" }} aria-hidden />
          <span>{li}</span>
        </li>
      ))}
    </ul>
  );
}
