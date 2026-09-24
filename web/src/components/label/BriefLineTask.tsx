"use client";

/**
 * "Does the report say this?" (the brief_support kind): one line of Prism's
 * brief and the report it was written from. The Phase 2 gate on citations
 * (correlation/cites.py, tools/gold_brief_cites) is measured from these answers:
 * a line people say the report does not state is printed as Prism's reading,
 * never as the report's.
 *
 * Set as the claim task is: the line in the record voice on a rule, the report's
 * closest passage, the whole report behind a disclosure, one ink pill for yes.
 * "I can't read <language>" is a skip, a fact about the labeller, never a vote.
 */

import type { LabelBriefLine } from "@/lib/api";

export function BriefLineTask({
  line, position, saving, onAnswer,
}: {
  line: LabelBriefLine;
  position: number;
  saving: boolean;
  onAnswer: (verdict: "yes" | "no" | "unsure" | "skip") => void;
}) {
  const r = line.report;
  const foreign = r.code && r.code !== "en";
  return (
    <div>
      <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-faint)" }}>
        question {position + 1}
      </p>
      <h1 className="mt-2 text-[23px] leading-[1.3]" style={{ fontFamily: "var(--font-display), serif", textWrap: "pretty" }}>
        Does the report say this?
      </h1>
      <p className="mt-2 text-[14px]" style={{ color: "var(--ink-muted)" }}>{line.story}</p>

      <figure className="mt-5 border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
        <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-faint)" }}>Prism&apos;s line</p>
        <blockquote className="mt-1 font-record text-[18px] leading-[1.55]">{line.line}</blockquote>
      </figure>

      <section className="mt-6 border-t pt-4" style={{ borderColor: "var(--line)" }} aria-label="The report">
        <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-faint)" }}>
          The report · {r.outlet} · {r.language}
        </p>
        <p className="mt-1 text-[15px] font-semibold leading-[1.4]" lang={r.code || undefined}>{r.title}</p>
        <p className="mt-2 text-[15.5px] leading-[1.65]" lang={r.code || undefined}>{r.excerpt}</p>
        <details className="mt-3">
          <summary className="cursor-pointer text-[14px] font-semibold" style={{ color: "var(--accent)" }}>
            Read the whole report
          </summary>
          <p className="mt-2 whitespace-pre-line text-[15px] leading-[1.65]" lang={r.code || undefined}>{r.text}</p>
          {r.url && (
            <a href={r.url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-[13.5px] underline underline-offset-4">
              Open it on {r.outlet}
            </a>
          )}
        </details>
      </section>

      <p className="mt-5 text-[14px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        Yes only if the report states everything in the line, in any words. A figure, name, cause or judgement the
        report does not state is a No. You are not judging whether the line is true.
      </p>
      {/* The claim task's answer row, as it is: one ink pill for yes, rules for the rest. */}
      <div className="mt-6 flex flex-wrap items-center gap-3 border-t pt-5" style={{ borderColor: "var(--line)" }}>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("yes")}
          className="h-11 rounded-full px-5 text-[14.5px] font-medium disabled:opacity-50"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Yes — the report says this
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("no")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
        >
          No — not what the report says
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("unsure")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
        >
          Not sure
        </button>
        {foreign && (
          <button
            type="button" disabled={saving} onClick={() => onAnswer("skip")}
            className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
            style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}
          >
            I can&apos;t read {r.language}
          </button>
        )}
      </div>
    </div>
  );
}
