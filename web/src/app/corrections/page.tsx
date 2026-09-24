import type { Metadata } from "next";
import Link from "next/link";
import { REASON_WORDS } from "@/components/RecordHistory";
import { fetchCorrections } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

// The public corrections log: every correction Prism has made to a record,
// newest first, with the reason and what was wrong. Publishing the mistakes is
// the point (strategy report, 2026-09-24).
export const revalidate = 300;

export const metadata: Metadata = {
  title: "Corrections",
  description: "Every correction Prism has made to a record, newest first, with the reason and what was wrong.",
  alternates: { canonical: "/corrections" },
};

const SHELL = "mx-auto w-full max-w-[var(--shell)] px-5 sm:px-8 xl:px-10";

export default async function CorrectionsPage() {
  const list = await fetchCorrections();
  return (
    <div className={`${SHELL} pb-24 pt-8 lg:pb-20 lg:pt-12`}>
      <div className="max-w-[var(--reading)]">
        <h1 className="font-record text-[34px] font-bold leading-[1.1] tracking-[-0.015em] sm:text-[42px]">Corrections</h1>
        <p className="mt-4 text-[17px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
          When a record is wrong, it is fixed and says so: the date, why, and what was wrong. The record keeps every
          earlier version, and this page lists every correction, newest first. A record that changed because new
          reports arrived is not a correction; its earlier versions are on the record itself.
        </p>
        {list === null ? (
          <p className="card mt-8 text-[15px]" style={{ color: "var(--danger)" }}>The corrections log cannot be reached right now.</p>
        ) : list.length === 0 ? (
          <p className="mt-8 border-t pt-4 text-[15px]" style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}>
            No corrections yet. When there is one, it is listed here.
          </p>
        ) : (
          <ol className="mt-8">
            {list.map((c) => (
              <li key={`${c.event_id}-${c.created_at}`} className="border-t py-4" style={{ borderColor: "var(--line)" }}>
                <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-3)" }}>
                  {shortDate(c.created_at)} · {REASON_WORDS[c.reason] ?? c.reason}
                </p>
                {c.event_id && c.title && (
                  <Link href={`/story/${c.event_id}#history`} className="font-record mt-1 block text-[19px] font-bold leading-[1.3] underline-offset-4 hover:underline">
                    {c.title}
                  </Link>
                )}
                <p className="mt-1 text-[15.5px] leading-[1.55]">{c.note}</p>
              </li>
            ))}
          </ol>
        )}
        <p className="mt-10 text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-3)" }}>
          Found something wrong? Say so from the foot of the record, or read <Link href="/about#accountability" className="underline underline-offset-4">who answers for Prism</Link>.
        </p>
      </div>
    </div>
  );
}
