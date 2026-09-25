"use client";

import { Ago } from "@/components/Ago";
import type { SourceRef, XPostOut } from "@/lib/api";
import { XIcon } from "@/components/icons";

/**
 * "On X": what the official accounts said about this story, as written.
 *
 * Signal, not coverage — none of this is in `sources`, none of it counts. The
 * row follows X's display rules for a post shown off-platform (avatar, name
 * and @handle linking to the profile; the text unaltered; the time linking to
 * the post; the X mark; a "View on X" link) and the record's own rules (mono
 * for provenance, no colour, a hairline above every unit). Off with
 * NEXT_PUBLIC_X_POSTS=0; the API is off separately with PRISM_X_ENABLED.
 */
export const X_POSTS = process.env.NEXT_PUBLIC_X_POSTS !== "0";

/**
 * The earliest post that is STRICTLY before the earliest report's own clock —
 * the one fact that lets the record say "first on X". Publisher timestamps on
 * both sides; a post that links a report we hold can never be first.
 */
export function firstOnX(posts: XPostOut[], sources: SourceRef[]): XPostOut | null {
  const firstReport = sources.map((s) => s.published_at).filter((t): t is string => !!t).sort()[0];
  if (!firstReport) return null;
  const earliest = posts.filter((p) => p.method !== "url").sort((a, b) => a.created_at.localeCompare(b.created_at))[0];
  return earliest && earliest.created_at < firstReport ? earliest : null;
}

function Avatar({ post }: { post: XPostOut }) {
  if (post.profile_image_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={post.profile_image_url} alt="" width={32} height={32} className="h-8 w-8 rounded-full grayscale" loading="lazy" referrerPolicy="no-referrer" />;
  }
  return (
    <span className="p-monogram" style={{ width: 32, height: 32, fontSize: 10 }} aria-hidden>
      {post.handle.slice(0, 2).toUpperCase()}
    </span>
  );
}

/** One post as X's display rules and the record agree on (Design System v2 · XPostCard). */
export function XPosts({ posts, sources }: { posts: XPostOut[]; sources: SourceRef[] }) {
  if (posts.length === 0) return null;
  const first = firstOnX(posts, sources);
  return (
    <div className="grid gap-3">
      {first && (
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
          First on X · @{first.handle} · <a href={first.url} target="_blank" rel="noopener noreferrer"><Ago iso={first.created_at} /></a>
        </p>
      )}
      <ol className="grid gap-3">
        {posts.map((p) => {
          const profile = `https://x.com/${p.handle}`;
          return (
            <li key={p.post_id} className="p-card grid gap-2.5" data-testid="x-post">
              <div className="flex items-center gap-2.5">
                <a href={profile} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0" aria-label={`${p.name} on X`}>
                  <Avatar post={p} />
                </a>
                <div className="min-w-0 flex-1">
                  <a href={profile} target="_blank" rel="noopener noreferrer" className="block truncate text-[14px] font-semibold leading-[1.25] hover:underline" style={{ color: "var(--ink)" }}>
                    {p.name}
                  </a>
                  <a href={profile} target="_blank" rel="noopener noreferrer" className="block font-mono text-[11.5px]" style={{ color: "var(--ink-3)" }}>
                    @{p.handle}
                  </a>
                </div>
                <span className="inline-flex shrink-0" style={{ color: "var(--ink-2)" }} aria-label="X">
                  <XIcon size={14} />
                </span>
              </div>
              <p className="whitespace-pre-wrap" style={{ font: "var(--t-body)", color: "var(--ink)", textWrap: "pretty", overflowWrap: "anywhere" }}>
                {p.text}
              </p>
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="p-count">
                  <Ago iso={p.created_at} />
                </a>
                {first?.post_id === p.post_id && <span className="p-badge p-badge--outline">First on X</span>}
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex min-h-[44px] items-center text-[13px] font-semibold lg:min-h-[32px]" style={{ color: "var(--accent)" }}>
                  View on X ↗
                </a>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
