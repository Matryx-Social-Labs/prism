import type { SourceRef } from "@/lib/api";

const FUNDING_LABEL: Record<string, string> = {
  state: "State-affiliated",
  public: "Public broadcaster",
};

/** A funding label is provenance: mono, quiet, no badge. */
function Funding({ funding }: { funding: string | null }) {
  if (!funding || !FUNDING_LABEL[funding]) return null;
  return (
    <span
      className="shrink-0 font-mono text-[9.5px] uppercase tracking-[0.06em]"
      style={{ color: "var(--ink-faint)" }}
    >
      {FUNDING_LABEL[funding]}
    </span>
  );
}

/**
 * The coaches: [n] outlet · headline · stance, one per hairline. The [n] is
 * the same index the quotes cite.
 */
export function SourceList({
  sources,
  sourceIndex,
}: {
  sources: SourceRef[];
  sourceIndex: Map<string, number>;
}) {
  return (
    <ul className="flex flex-col">
      {sources.map((s) => (
        <li
          key={s.article_id}
          className="rule-live grid grid-cols-[28px_1fr] gap-x-2 py-2.5 text-[13.5px]"
        >
          <span
            className="font-mono text-[11px] leading-[1.7]"
            style={{ color: "var(--ink-faint)" }}
          >
            [{sourceIndex.get(s.article_id)}]
          </span>
          <span className="min-w-0">
            <span className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-medium" style={{ color: "var(--ink)" }}>
                {s.source_name}
              </span>
              <Funding funding={s.funding} />
              {s.stance && (
                <span
                  className="text-[11.5px]"
                  style={{ color: "var(--ink-faint)" }}
                >
                  {s.stance}
                </span>
              )}
            </span>
            {s.url ? (
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block underline-offset-4 hover:underline"
                style={{ color: "var(--ink-muted)" }}
              >
                {s.title}
              </a>
            ) : (
              <span
                className="block"
                style={{ color: "var(--ink-muted)" }}
              >
                {s.title}
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** One index for [n], shared by the quotes and the coaches. */
export function indexSources(sources: SourceRef[]): Map<string, number> {
  return new Map(sources.map((s, i) => [s.article_id, i + 1]));
}
