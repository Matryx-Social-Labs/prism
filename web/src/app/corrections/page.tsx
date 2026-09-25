import type { Metadata } from "next";
import Link from "next/link";
import { PageTitle } from "@/components/reading/parts";
import { REASON_WORDS } from "@/components/RecordHistory";
import { StatusPill } from "@/components/StatusPill";
import { Alert, BackBar, EmptyState } from "@/components/ui";
import { fetchCorrections } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

// The public corrections log: every correction Prism has made to a record,
// newest first, with the reason and what was wrong. Publishing the mistakes is
// the point (strategy report, 2026-09-24). Claude Design · ReadingB Corrections:
// the log prints what the API records — date, reason, note — and nothing it
// does not (no "was / now" pair: a correction is one note).
export const revalidate = 300;

export const metadata: Metadata = {
  title: "Corrections",
  description: "Every correction Prism has made to a record, newest first, with the reason and what was wrong.",
  alternates: { canonical: "/corrections" },
};

export default async function CorrectionsPage() {
  const list = await fetchCorrections();
  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[720px] grid-cols-[minmax(0,1fr)] gap-[18px] px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-2">
          <PageTitle>Corrections</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            When a record is wrong, it is fixed and says so: the date, why, and what was wrong. The record keeps every
            earlier version, and this page lists every correction, newest first. A record that changed because new
            reports arrived is not a correction; its earlier versions are on the record itself.
          </p>
        </header>
        {list === null ? (
          <Alert tone="error" title="The corrections log cannot be reached right now.">Try again in a minute.</Alert>
        ) : list.length === 0 ? (
          <EmptyState title="No corrections yet">When there is one, it is listed here with the date, the reason and what was wrong.</EmptyState>
        ) : (
          <ol>
            {list.map((c) => (
              <li key={`${c.event_id}-${c.created_at}`} className="grid gap-2 border-t py-4" style={{ borderColor: "var(--line)" }}>
                <p className="flex flex-wrap items-center gap-2">
                  <StatusPill status="corrected" />
                  <span className="p-meta">
                    <time dateTime={c.created_at} className="p-meta__prov">{shortDate(c.created_at).toUpperCase()}</time>
                    <span className="p-meta__sep" />
                    <span style={{ font: "500 13px/1.3 var(--font-read)", color: "var(--ink-2)" }}>{REASON_WORDS[c.reason] ?? c.reason}</span>
                  </span>
                </p>
                {c.event_id && c.title && (
                  <Link href={`/story/${c.event_id}`} className="text-balance underline-offset-4 hover:underline" style={{ font: "var(--t-title)", color: "var(--ink)" }}>
                    {c.title}
                  </Link>
                )}
                <p style={{ font: "var(--t-body-s)" }}>{c.note}</p>
                {c.event_id && (
                  <Link href={`/story/${c.event_id}#history`} className="p-link justify-self-start" style={{ font: "600 13.5px/1.3 var(--font-read)" }}>
                    Earlier versions →
                  </Link>
                )}
              </li>
            ))}
          </ol>
        )}
        <p className="mt-4" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          Found something wrong? Say so from the foot of the record, or read <Link href="/about#accountability" className="p-link">who answers for Prism</Link>.
        </p>
      </div>
    </>
  );
}
