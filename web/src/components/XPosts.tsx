"use client";

import type { SourceRef, XPostOut } from "@/lib/api";
import { relativeTime } from "@/lib/dateline";
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
    return <img src={post.profile_image_url} alt="" width={24} height={24} className="h-6 w-6 rounded-full grayscale" loading="lazy" />;
  }
  return (
    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full font-mono text-[10px]" style={{ background: "var(--accent-soft)", color: "var(--ink-2)" }} aria-hidden>
      {post.name.slice(0, 1)}
    </span>
  );
}

export function XPosts({ posts, sources }: { posts: XPostOut[]; sources: SourceRef[] }) {
  if (posts.length === 0) return null;
  const first = firstOnX(posts, sources);
  return (
    <div className="border-l-2 pl-4 sm:pl-5" style={{ borderColor: "var(--line-strong)" }}>
      {first && (
        <p className="mb-3 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
          First on X · @{first.handle} · {relativeTime(first.created_at)}
        </p>
      )}
      <ol className="divide-y" style={{ borderColor: "var(--line)" }}>
        {posts.map((p) => {
          const profile = `https://x.com/${p.handle}`;
          return (
            <li key={p.post_id} className="py-5" data-testid="x-post">
              <div className="flex items-center gap-2">
                <a href={profile} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0" aria-label={`${p.name} on X`}>
                  <Avatar post={p} />
                </a>
                <a href={profile} target="_blank" rel="noopener noreferrer" className="text-[12.5px] font-semibold underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>
                  {p.name}
                </a>
                <a href={profile} target="_blank" rel="noopener noreferrer" className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                  @{p.handle}
                </a>
                <span className="ml-auto inline-flex" style={{ color: "var(--ink-3)" }} aria-label="X">
                  <XIcon size={14} />
                </span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-[15.5px] leading-[1.65]" style={{ color: "var(--ink)", textWrap: "pretty" }}>
                {p.text}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px]" style={{ color: "var(--ink-3)" }}>
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-mono text-[11px]">
                  <time dateTime={p.created_at}>{relativeTime(p.created_at)}</time>
                </a>
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-semibold underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
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
