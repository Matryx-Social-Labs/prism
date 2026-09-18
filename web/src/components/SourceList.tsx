import type { SourceRef } from "@/lib/api";
import { ORIGIN_LABEL, OutletIcon, type Origin } from "@/components/Coverage";
import { relativeTime } from "@/lib/dateline";

const FUNDING_LABEL: Record<string, string> = {
  state: "State-affiliated",
  public: "Public broadcaster",
};

export function fallbackCode(name: string | null | undefined): string {
  const words = (name ?? "").replace("—", " ").split(/\s+/).filter((w) => w && !/^(the|of|news|&|and)$/i.test(w));
  if (words.length === 0) return "?";
  return (words.length === 1 ? words[0].slice(0, 2) : words.slice(0, 3).map((w) => w[0]).join("")).toUpperCase();
}

/**
 * One report as the reader sees it (DESIGN.md § Report card): the outlet's
 * icon and name, when it published, the headline the outlet wrote, and the
 * `[n]` that every quote citing it uses. The whole card opens the article.
 */
export function ReportCard({ source, n, compact = false }: { source: SourceRef; n?: number; compact?: boolean }) {
  const s = source;
  const origin = s.origin ? ORIGIN_LABEL[s.origin as Origin] : null;
  const funding = s.funding ? FUNDING_LABEL[s.funding] : null;
  const inner = (
    <>
      <span className="flex items-center gap-2">
        <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={compact ? 24 : 28} />
        <span className="min-w-0 flex-1 truncate text-[12.5px] font-semibold" style={{ color: "var(--ink-2)" }}>{s.source_name}</span>
        {s.published_at && (
          <time dateTime={s.published_at} className="shrink-0 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
            {relativeTime(s.published_at)}
          </time>
        )}
      </span>
      <span className={`mt-2 block font-medium leading-[1.35] [display:-webkit-box] [-webkit-box-orient:vertical] overflow-hidden ${compact ? "text-[13.5px] [-webkit-line-clamp:3]" : "text-[15px] [-webkit-line-clamp:3]"}`} style={{ color: "var(--ink)" }}>
        {s.title}
      </span>
      {(n != null || origin || funding || s.stance) && (
        <span className="mt-2 flex items-center gap-2 text-[11.5px]" style={{ color: "var(--ink-3)" }}>
          {n != null && <span className="font-mono text-[11px]">[{n}]</span>}
          {origin && <span>{origin}</span>}
          {funding && <span>· {funding}</span>}
          {s.stance && <span>· {s.stance}</span>}
        </span>
      )}
    </>
  );
  const cls = `row-card block ${compact ? "px-3 py-2.5" : "px-4 py-3.5"}`;
  return s.url ? (
    <a href={s.url} target="_blank" rel="noopener noreferrer" className={cls} aria-label={`${s.source_name}: ${s.title}`}>
      {inner}
    </a>
  ) : (
    <span className={cls}>{inner}</span>
  );
}

/**
 * The reports behind a story as cards. `compact` is the desktop rail's
 * variant; both carry `[n]`, the same index the quotes cite.
 */
export function SourceList({
  sources,
  sourceIndex,
  compact = false,
}: {
  sources: SourceRef[];
  sourceIndex: Map<string, number>;
  compact?: boolean;
}) {
  return (
    <ul className={`flex flex-col ${compact ? "gap-2" : "gap-2.5"}`}>
      {sources.map((s, i) => (
        <li key={s.article_id ?? `${s.source_name}-${i}`}>
          <ReportCard source={s} n={sourceIndex.get(s.article_id)} compact={compact} />
        </li>
      ))}
    </ul>
  );
}

/** One index for [n], shared by the quotes and the report cards. */
export function indexSources(sources: SourceRef[]): Map<string, number> {
  return new Map(sources.map((s, i) => [s.article_id, i + 1]));
}
