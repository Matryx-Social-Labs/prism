import Link from "next/link";
import type { EventDetail, FollowUpRef } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { followRel } from "@/lib/seo";
import { SectionHead as Head } from "@/components/SectionHead";

/**
 * Earlier and later: other records a verifier judged to be earlier or later
 * developments of this one (api/routes/events.follow_ups), in the order they
 * were first reported, each dated by its first report. They
 * are links between records, not the story's timeline — that is "How this
 * story unfolded", and only once its boundary is verified. Absent, never
 * empty, when there are none (and on an older payload with no field).
 */
export function FollowUps({ followUps, className }: { followUps: EventDetail["follow_ups"]; className?: string }) {
  const { earlier, later } = followUps ?? { earlier: [], later: [] };
  if (!earlier.length && !later.length) return null;
  return (
    <section className={className} aria-labelledby="follow-ups-title">
      <Head
        id="follow-ups-title"
        title="Earlier and later"
        hint="Other records that software judged to be earlier or later developments of this one, oldest first. Links between records, not the story's full timeline."
      />
      <div className="mt-3 grid gap-5">
        <Side label="Earlier in this story" refs={earlier} />
        <Side label="Later in this story" refs={later} />
      </div>
    </section>
  );
}

function Side({ label, refs }: { label: string; refs: FollowUpRef[] }) {
  if (!refs.length) return null;
  return (
    <div>
      <h3 className="p-eyebrow mb-1.5">{label}</h3>
      <ul>
        {refs.map((r) => (
          <li key={r.id} className="grid gap-1 border-t py-3" style={{ borderColor: "var(--line)" }}>
            {/* A record asks to be indexed from its second outlet (lib/seo.followRel); unknown stays plain. */}
            <Link
              href={`/story/${r.id}`}
              rel={followRel(r.source_count == null ? undefined : r.source_count > 1)}
              className="underline-offset-4 hover:underline"
              style={{ font: "var(--t-title-s)", color: "var(--ink)" }}
            >
              {r.title}
            </Link>
            <p className="p-count">
              {shortDate(r.first_published_at ?? r.first_seen_at)}
              {r.source_count != null && ` · ${r.source_count} ${r.source_count === 1 ? "outlet" : "outlets"}`}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
