"use client";

/**
 * A labelling guide, rendered from what the API sends (common/label_guides.py).
 * The words are not in this file on purpose: they reach only an applicant's
 * account or a batch's own invite, never the site's public JavaScript
 * (founder, 2026-09-23; CI checks with web/scripts/check-no-guides.mjs).
 *
 * Design System v2 · label/GuideInShort + label/Verdict: the question as the
 * title, "In short" first so a reader who will not read the rest still leaves
 * with the rule, then DO / DO NOT, then worked examples as verdicts. A verdict
 * is always a word with its icon on a rule — never colour, never an icon alone.
 */

import type { ReactNode } from "react";

import { Check, Dash } from "@/components/icons";
import { MARK, Verdict, markKind } from "@/components/label/parts";
import type { GuideBlock, LabelGuide } from "@/lib/api";

/** **strong**, *emphasis* and ==highlight==, and nothing else. */
export function Rich({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|==[^=]+==|\*[^*]+\*)/g).filter(Boolean);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**")) return <strong key={i} style={{ color: "var(--ink)" }}>{p.slice(2, -2)}</strong>;
        if (p.startsWith("==")) return <mark key={i} style={MARK}>{p.slice(2, -2)}</mark>;
        if (p.startsWith("*")) return <em key={i}>{p.slice(1, -1)}</em>;
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

/** "TICK — a real pair" → the verdict word, and what it is about. */
function splitHead(head: string): [string | undefined, string] {
  const at = head.indexOf(" — ");
  return at < 0 ? [undefined, head] : [head.slice(0, at), head.slice(at + 3)];
}

function RuleList({ title, mark, rules }: { title: string; mark: "yes" | "no"; rules: string[] }) {
  const Icon = mark === "yes" ? Check : Dash;
  return (
    <section>
      <h2 className="p-eyebrow mb-1.5">{title}</h2>
      <ul className="grid gap-1.5">
        {rules.map((r) => (
          <li key={r} className="grid grid-cols-[20px_minmax(0,1fr)] gap-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink)" }}>
            <span aria-hidden className="pt-[3px]"><Icon size={16} /></span>
            <span><Rich text={r} /></span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The rule in one sentence on a sunken block, what comes between, then Do / Do not. */
export function GuideInShort({ rule, dos, donts, children }: { rule: string; dos: string[]; donts: string[]; children?: ReactNode }) {
  return (
    <div className="grid gap-4">
      <section className="p-4" style={{ background: "var(--sunken)", borderRadius: "var(--r-md)" }}>
        <h2 className="p-eyebrow">In short</h2>
        <p className="mt-1.5" style={{ font: "600 17px/1.45 var(--font-read)", color: "var(--ink)" }}>{rule}</p>
      </section>
      {children}
      {(dos.length > 0 || donts.length > 0) && (
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          {dos.length > 0 && <RuleList title="Do" mark="yes" rules={dos} />}
          {donts.length > 0 && <RuleList title="Do not" mark="no" rules={donts} />}
        </div>
      )}
    </div>
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
    <article className="grid max-w-[640px] gap-6 pb-8">
      <header>
        <h1 style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{guide.question}</h1>
        <p className="p-count mt-2">
          About {guide.minutes} {guide.minutes === 1 ? "minute" : "minutes"} to read
        </p>
      </header>

      <GuideInShort rule={guide.in_short} dos={guide.do} donts={guide.dont}>
        {guide.lede.map((para) => (
          <p key={para} style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            <Rich text={para} />
          </p>
        ))}
      </GuideInShort>

      {guide.examples.length > 0 && (
        <section>
          {guide.examples_label && <h2 className="p-eyebrow mb-1.5">{guide.examples_label}</h2>}
          {guide.examples.map((ex) => {
            const [word, about] = splitHead(ex.head);
            return (
              <Verdict key={ex.head} kind={markKind(ex.mark)} word={word}>
                {/* Written by us rather than seen in the corpus: it says so. */}
                {ex.illustration && <span className="p-badge p-badge--dashed justify-self-start">ILLUSTRATION</span>}
                <p className="font-semibold" style={{ color: "var(--ink)" }}><Rich text={about} /></p>
                <p style={{ color: "var(--ink-2)" }}><Rich text={ex.body} /></p>
              </Verdict>
            );
          })}
        </section>
      )}

      {guide.decide && <HowToDecide blocks={guide.decide.blocks} closing={guide.decide.closing} open />}

      <div>
        <button type="button" onClick={onStart} className="p-btn p-btn--primary p-btn--lg">
          {action ?? guide.start}
        </button>
        {guide.after && (
          <p className="mt-3" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
            {guide.after}
          </p>
        )}
      </div>
    </article>
  );
}

/** "How to decide": the worked pair beside each task, collapsed once the
 *  labeller is going (it is reference then, not instruction). A tick sits on
 *  the solid rule, a leave on the dashed one — rule and word, not colour. */
export function HowToDecide({ blocks, closing, open = false }: { blocks: GuideBlock[]; closing: string; open?: boolean }) {
  return (
    <details open={open} className="border-t pt-1" style={{ borderColor: "var(--line)" }}>
      <summary
        className="flex min-h-11 cursor-pointer list-none items-center text-[14px] font-semibold [&::-webkit-details-marker]:hidden"
        style={{ color: "var(--accent)" }}
      >
        How to decide
      </summary>
      <div className="mt-1">
        {blocks.map((b) => (
          <Verdict key={b.label} kind={markKind(b.mark)} word={b.label}>
            {b.lines.map((line) => (
              <p key={line} style={{ color: "var(--ink)" }}>
                <Rich text={line} />
              </p>
            ))}
            <p style={{ color: "var(--ink-2)" }}>
              <Rich text={b.body} />
            </p>
          </Verdict>
        ))}
        <p className="border-t pt-3" style={{ borderColor: "var(--line)", font: "var(--t-body-s)", color: "var(--ink-2)" }}>
          <Rich text={closing} />
        </p>
      </div>
    </details>
  );
}
