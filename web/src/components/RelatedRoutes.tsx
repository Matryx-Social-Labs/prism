import Link from "next/link";
import type { RelatedStory } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { followRel } from "@/lib/seo";

/**
 * Related routes: different stories that touch this one, listed beside the
 * route and never drawn on it. The relation is said in the record's own
 * terms — the cast the two share, or a causal note the thread linker wrote
 * across the boundary — with the story's size and whether it is moving.
 *
 * `indexable` is the page's own story's: a RelatedStory carries no status,
 * and none is needed, since a boundary status is one switch for every story
 * (common/stories.STORY_BOUNDARY_STATUS) — while it reads provisional, no
 * story asks to be indexed, so these links are nofollow (lib/seo followRel).
 */
export function RelatedRoutes({ related, indexable }: { related: RelatedStory[]; indexable?: boolean }) {
  if (!related.length) return null;
  return (
    <ul>
      {related.map((r) => {
        const how = [
          r.causal ? "linked by a causal note" : null,
          r.shared_cast.length ? `shares ${r.shared_cast.slice(0, 3).join(" · ")}` : null,
        ].filter(Boolean).join(" · ");
        return (
          <li key={r.slug} className="grid gap-1 border-t py-3" style={{ borderColor: "var(--line)" }}>
            <Link href={`/trending/${r.slug}`} rel={followRel(indexable)} className="underline-offset-4 hover:underline" style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>{r.label}</Link>
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
              {how} · {r.developments} related {r.developments === 1 ? "event" : "events"} ·{" "}
              {r.velocity > 0 ? <span style={{ color: "var(--ink)", fontWeight: 600 }}>moving</span> : r.last_updated_at ? `quiet since ${shortDate(r.last_updated_at)}` : "quiet"}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
