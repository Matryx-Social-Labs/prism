import Link from "next/link";
import type { RelatedStory } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

/**
 * Related routes: different stories that touch this one, listed beside the
 * route and never drawn on it. The relation is said in the record's own
 * terms — the cast the two share, or a causal note the thread linker wrote
 * across the boundary — with the story's size and whether it is moving.
 */
export function RelatedRoutes({ related }: { related: RelatedStory[] }) {
  if (!related.length) return null;
  return (
    <div className="mt-6">
      <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>
        Related routes · different stories, not part of this one
      </p>
      <ul className="mt-1">
        {related.map((r) => {
          const how = [
            r.causal ? "linked by a causal note" : null,
            r.shared_cast.length ? `shares ${r.shared_cast.slice(0, 3).join(" · ")}` : null,
          ].filter(Boolean).join(" · ");
          return (
            <li key={r.slug} className="rule-live py-2.5">
              <Link href={`/trending/${r.slug}`} className="text-[15px] leading-[1.4] underline-offset-4 hover:underline">{r.label}</Link>
              <p className="mt-1 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
                {how} · {r.developments} {r.developments === 1 ? "development" : "developments"} ·{" "}
                {r.velocity > 0 ? <span style={{ color: "var(--ink)" }}>moving</span> : r.last_updated_at ? `quiet since ${shortDate(r.last_updated_at)}` : "quiet"}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
