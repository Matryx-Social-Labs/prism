"use client";

import { useState } from "react";
import { fetchVersions, type RecordCorrection, type RecordVersion } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { sentences } from "@/lib/sentences";

/** Why a record was corrected, in a reader's words. */
export const REASON_WORDS: Record<RecordCorrection["reason"], string> = {
  source_correction: "The outlet corrected its report",
  prism_error: "Prism's error",
};

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
            <li key={c.created_at + c.note} className="border-t py-3 first:border-t-0" style={{ borderColor: "var(--line)" }}>
              <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-3)" }}>
                Corrected {shortDate(c.created_at)} · {REASON_WORDS[c.reason] ?? c.reason}
              </p>
              <p className="mt-1 text-[15px] leading-[1.55]">{c.note}</p>
            </li>
          ))}
        </ul>
      )}
      {versions === null ? (
        <button type="button" onClick={open} disabled={loading} className="self-start text-[14.5px] font-semibold underline-offset-4 hover:underline disabled:opacity-60" style={{ color: "var(--accent)" }}>
          {loading ? "Loading earlier versions…" : "Earlier versions of this record"}
        </button>
      ) : versions.length === 0 ? (
        <p className="text-[14.5px]" style={{ color: "var(--ink-3)" }}>This record has not changed since it was first written.</p>
      ) : (
        <ol aria-label="Earlier versions" className="flex flex-col">
          {versions.map((v) => (
            <li key={v.replaced_at} className="border-t py-3 first:border-t-0" style={{ borderColor: "var(--line)" }}>
              <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-3)" }}>Until {shortDate(v.replaced_at)}</p>
              {v.title && <p className="font-record mt-1 text-[16px] font-bold leading-[1.35]">{v.title}</p>}
              {v.brief && (
                <ul className="mt-1.5 list-disc pl-5 text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
                  {sentences(v.brief).map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              )}
            </li>
          ))}
        </ol>
      )}
      {failed && <p className="text-[14px]" style={{ color: "var(--danger)" }}>The earlier versions could not be loaded. Try again.</p>}
    </div>
  );
}
