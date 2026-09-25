"use client";

import { Ago } from "@/components/Ago";
import { useState } from "react";
import { OutletIcon } from "@/components/Coverage";
import { ArrowRight } from "@/components/icons";
import type { SourceRef } from "@/lib/api";
import { fallbackCode } from "@/lib/sources";

const FOLD = 5;

/**
 * What changed (Design System v2 · ChangeTimeline): every report on the
 * story, newest first, on one hairline spine — the outlet's mark, who and
 * when, the `[n]` the quotes cite, and the outlet's own headline opening the
 * article. Five, then the rest on request.
 */
export function ChangeTimeline({ reports, sourceIndex }: { reports: SourceRef[]; sourceIndex: Map<string, number> }) {
  const [all, setAll] = useState(false);
  const list = all ? reports : reports.slice(0, FOLD);
  return (
    <div>
      <ol className="grid">
        {list.map((r, i) => {
          const n = sourceIndex.get(r.article_id);
          return (
            <li key={r.article_id ?? i} className="grid grid-cols-[20px_minmax(0,1fr)] gap-3 pb-3.5">
              <span className="relative flex justify-center">
                {i < list.length - 1 && <span aria-hidden className="absolute bottom-[-14px] top-[22px] w-px" style={{ background: "var(--line-strong)" }} />}
                <span className="relative"><OutletIcon domain={r.domain} code={r.code ?? fallbackCode(r.source_name)} name={r.source_name} size={20} /></span>
              </span>
              <div className="grid min-w-0 gap-0.5">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-[13px] font-semibold leading-[1.3]">{r.source_name}</span>
                  {r.published_at ? <Ago iso={r.published_at} className="p-count" /> : <span className="p-count">time unknown</span>}
                  {n != null && <span className="p-count font-mono">[{n}]</span>}
                </div>
                {r.url ? (
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="hover:underline" style={{ font: "500 15px/1.4 var(--font-read)", color: "var(--ink)", textUnderlineOffset: 4, overflowWrap: "anywhere" }}>
                    {r.title} <ArrowRight size={13} className="inline align-[-1px]" />
                  </a>
                ) : (
                  <p style={{ font: "500 15px/1.4 var(--font-read)", overflowWrap: "anywhere" }}>{r.title}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      {!all && reports.length > FOLD && (
        <button type="button" onClick={() => setAll(true)} className="p-btn p-btn--text p-btn--sm">
          Show all {reports.length}
        </button>
      )}
    </div>
  );
}
