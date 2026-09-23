"use client";

/**
 * A labelling guide, rendered from what the API sends (common/label_guides.py).
 * The words are not in this file on purpose: they reach only an applicant's
 * account or a batch's own invite, never the site's public JavaScript
 * (founder, 2026-09-23; CI checks with web/scripts/check-no-guides.mjs).
 *
 * The shape follows the legal pages (DESIGN.md): the question as the title,
 * "In short" first so a reader who will not read the rest still leaves with the
 * rule, then DO / DO NOT and worked examples on hairlines. A verdict is always
 * a word, with a Check or a Dash beside it — never colour, and never an icon
 * alone (the Legend Rule). No eyebrow above the title; the reading time is a
 * provenance line under it.
 */

import { Check, Dash } from "@/components/icons";
import type { GuideBlock, LabelGuide } from "@/lib/api";

/** **strong**, *emphasis* and ==highlight==, and nothing else. */
export function Rich({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|==[^=]+==|\*[^*]+\*)/g).filter(Boolean);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**")) return <strong key={i} style={{ color: "var(--ink)" }}>{p.slice(2, -2)}</strong>;
        if (p.startsWith("==")) return <mark key={i} style={{ background: "var(--sunken)", color: "inherit" }}>{p.slice(2, -2)}</mark>;
        if (p.startsWith("*")) return <em key={i}>{p.slice(1, -1)}</em>;
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

function Mark({ mark }: { mark?: "yes" | "no" }) {
  if (!mark) return <span aria-hidden className="inline-block w-[14px] shrink-0" />;
  return (
    <span aria-hidden className="mt-[3px] inline-flex shrink-0" style={{ color: "var(--ink)" }}>
      {mark === "yes" ? <Check size={14} /> : <Dash size={14} />}
    </span>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  // The label voice (DESIGN.md scale): Hind 12.5, caps, tracked — not mono,
  // which is for provenance only.
  return (
    <h2 className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
      {children}
    </h2>
  );
}

/** The whole guide: read before the first task, and on /label/learn/<kind>. */
export function GuidePrimer({
  guide,
  onStart,
  action,
}: {
  guide: LabelGuide;
  onStart: () => void;
  action?: string;
}) {
  return (
    <article className="mx-auto max-w-[640px] pt-2">
      <h1 className="text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        {guide.question}
      </h1>
      <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
        ABOUT {guide.minutes} {guide.minutes === 1 ? "MINUTE" : "MINUTES"} TO READ
      </p>

      <section className="mt-6 border-t pt-4" style={{ borderColor: "var(--line)" }}>
        <Label>In short</Label>
        <p className="mt-1.5 text-[16px] leading-[1.55]" style={{ color: "var(--ink)" }}>
          {guide.in_short}
        </p>
      </section>

      {guide.lede.map((para) => (
        <p key={para} className="mt-5 text-[15px] leading-[1.65]" style={{ color: "var(--ink-2)" }}>
          <Rich text={para} />
        </p>
      ))}

      {guide.do.length > 0 && <Rules title="Do" mark="yes" rules={guide.do} />}
      {guide.dont.length > 0 && <Rules title="Do not" mark="no" rules={guide.dont} />}

      {guide.examples.length > 0 && (
        <section className="mt-8">
          {guide.examples_label && <Label>{guide.examples_label}</Label>}
          <ul className="mt-2">
            {guide.examples.map((ex) => (
              <li key={ex.head} className="border-t py-3" style={{ borderColor: "var(--line)" }}>
                {ex.illustration && (
                  <p className="mb-1 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                    ILLUSTRATION
                  </p>
                )}
                <p className="flex gap-2.5 text-[14.5px] font-semibold leading-snug" style={{ color: "var(--ink)" }}>
                  <Mark mark={ex.mark} />
                  <span>{ex.head}</span>
                </p>
                <p className="mt-1 pl-[24px] text-[14px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
                  {ex.body}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {guide.decide && <HowToDecide blocks={guide.decide.blocks} closing={guide.decide.closing} open />}

      <button type="button" onClick={onStart} className="btn btn-primary mt-8">
        {action ?? guide.start}
      </button>
      {guide.after && (
        <p className="mt-3 text-[13px]" style={{ color: "var(--ink-3)" }}>
          {guide.after}
        </p>
      )}
    </article>
  );
}

function Rules({ title, mark, rules }: { title: string; mark: "yes" | "no"; rules: string[] }) {
  return (
    <section className="mt-7">
      <Label>{title}</Label>
      <ul className="mt-2">
        {rules.map((r) => (
          <li key={r} className="flex gap-2.5 border-t py-2.5 text-[14.5px] leading-[1.55]" style={{ borderColor: "var(--line)" }}>
            <Mark mark={mark} />
            <span style={{ color: mark === "yes" ? "var(--ink)" : "var(--ink-2)" }}>
              <Rich text={r} />
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** "How to decide": the worked pair beside each task, collapsed once the
 *  labeller is going (it is reference then, not instruction). A tick is set
 *  on the heavier rule, a leave on the hairline — rule weight, not colour. */
export function HowToDecide({ blocks, closing, open = false }: { blocks: GuideBlock[]; closing: string; open?: boolean }) {
  return (
    <details open={open} className="mt-8 border-t pt-5" style={{ borderColor: "var(--line)" }}>
      <summary className="min-h-[44px] cursor-pointer text-[14.5px] font-medium" style={{ color: "var(--ink)" }}>
        How to decide
      </summary>
      <div className="mt-3 space-y-5">
        {blocks.map((b) => (
          <div
            key={b.label}
            className="pl-4"
            style={{ borderLeft: b.mark === "yes" ? "2px solid var(--ink)" : "1px solid var(--line-strong)" }}
          >
            <p className="flex items-center gap-2">
              <Mark mark={b.mark} />
              <span className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
                {b.label}
              </span>
            </p>
            {b.lines.map((line) => (
              <p key={line} className="mt-2 text-[14.5px]" style={{ color: b.mark === "yes" ? "var(--ink)" : "var(--ink-2)" }}>
                <Rich text={line} />
              </p>
            ))}
            <p className="mt-2 text-[13.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
              <Rich text={b.body} />
            </p>
          </div>
        ))}
        <p className="text-[13.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
          <Rich text={closing} />
        </p>
      </div>
    </details>
  );
}
