"use client";

import { useState } from "react";
import { fetchVersions, type RecordCorrection, type RecordVersion } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import { Alert } from "@/components/ui";
import { istTime, shortDate } from "@/lib/dateline";
import { sentences } from "@/lib/sentences";

/** Why a record was corrected, in a reader's words. */
export const REASON_WORDS: Record<RecordCorrection["reason"], string> = {
  source_correction: "The outlet corrected its report",
  prism_error: "Prism's error",
};

/** The most versions the API serves for one record (api/routes/corrections.py, LIMIT 50). */
const VERSIONS_SERVED = 50;

/**
 * A record's corrections and its earlier versions. A correction is printed
 * whenever there is one; the versions (every replaced headline, summary and
 * free brief, kept by the database) load only when asked for, because most
 * readers never will and the list can be long.
 */
export function RecordHistory({ eventId, corrections }: { eventId: string; corrections: RecordCorrection[] }) {
  const [versions, setVersions] = useState<RecordVersion[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const open = () => {
    setLoading(true);
    setFailed(false);
    fetchVersions(eventId).then((v) => setVersions(v.versions)).catch(() => setFailed(true)).finally(() => setLoading(false));
  };
  return (
    <div className="flex flex-col gap-4">
      {corrections.length > 0 && (
        <ul aria-label="Corrections">
          {corrections.map((c) => (
            <li key={c.created_at + c.note} className="grid gap-1.5 border-t py-3 first:border-t-0" style={{ borderColor: "var(--line)" }}>
              <p className="flex flex-wrap items-center gap-2">
                <StatusPill status="corrected" />
                <span className="p-meta">
                  <time dateTime={c.created_at} className="p-meta__prov">{shortDate(c.created_at)}</time>
                  <span className="p-meta__sep" />
                  <span style={{ font: "500 13px/1.3 var(--font-read)", color: "var(--ink-2)" }}>{REASON_WORDS[c.reason] ?? c.reason}</span>
                </span>
              </p>
              <p style={{ font: "var(--t-body-s)" }}>{c.note}</p>
            </li>
          ))}
        </ul>
      )}
      {versions === null ? (
        <button type="button" onClick={open} disabled={loading} className="p-link self-start disabled:opacity-60" style={{ font: "600 14.5px/1.3 var(--font-read)" }}>
          {loading ? "Loading earlier versions…" : "Earlier versions of this record"}
        </button>
      ) : versions.length === 0 ? (
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>This record has not changed since it was first written.</p>
      ) : (
        // Claude Design · ReadingB "Earlier versions": a mono version number in a
        // 44px column, when the version was replaced, and what it said. The number
        // counts up from the first version, so it is printed only when the list is
        // whole (the API returns at most VERSIONS_SERVED, newest first).
        <ol aria-label="Earlier versions">
          {versions.map((v, i) => (
            <li key={v.replaced_at} className="grid grid-cols-[44px_minmax(0,1fr)] gap-3 border-t py-3.5 first:border-t-0" style={{ borderColor: "var(--line)" }}>
              <span className="p-mono" style={{ fontSize: 13, color: "var(--ink)" }}>{versions.length < VERSIONS_SERVED ? `v${versions.length - i}` : ""}</span>
              <div className="grid min-w-0 gap-1">
                <p className="p-meta">
                  <span className="p-meta__subject">Until</span>
                  <time dateTime={v.replaced_at} className="p-meta__prov">{shortDate(v.replaced_at)} {istTime(v.replaced_at)} IST</time>
                </p>
                {v.title && <p style={{ font: "var(--t-title-s)" }}>{v.title}</p>}
                {v.brief && (
                  <ul className="list-disc pl-5" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                    {sentences(v.brief).map((s, j) => <li key={j}>{s}</li>)}
                  </ul>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
      {failed && <Alert tone="error">The earlier versions could not be loaded. Try again.</Alert>}
    </div>
  );
}
