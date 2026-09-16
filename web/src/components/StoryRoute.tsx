"use client";

import { useEffect, useState } from "react";
import { BranchTree } from "@/components/BranchTree";
import { ChevronDown } from "@/components/icons";
import { RouteMap } from "@/components/RouteMap";
import { fetchTrendingStory, type TrendingStoryDetail } from "@/lib/api";

/**
 * The route on the ticket: this development's place on its story, drawn as
 * the rail map in its compact form (this station and its neighbours), with
 * every station as a list beneath, folded, for the reader who wants the
 * table and for the screen reader.
 *
 * The event payload carries no arc; /trending/{slug} owns it, built from the
 * story's frozen member set, so the ticket and the route page can never
 * disagree about which developments exist. No slug, no section: a story with
 * one development has no route to show.
 */
export function StoryRoute({ slug, currentId, onLoad }: { slug: string; currentId: string; onLoad?: (s: TrendingStoryDetail | null) => void }) {
  const [story, setStory] = useState<TrendingStoryDetail | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    fetchTrendingStory(slug).then((s) => {
      if (cancelled) return;
      setStory(s);
      onLoad?.(s);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  if (story === undefined) {
    return (
      <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }} aria-busy="true">
        Loading the story…
      </p>
    );
  }
  if (!story?.branches || story.branches.nodes.length < 2) return null;

  return (
    <div>
      <RouteMap tree={story.branches} developments={story.developments} currentId={currentId} compact />
      <details className="rule-live mt-2 group">
        <summary className="flex cursor-pointer list-none items-center gap-2 py-3 font-mono text-[11px]" style={{ color: "var(--ink-muted)" }}>
          <ChevronDown className="transition-transform group-open:rotate-180" />
          All developments
        </summary>
        <BranchTree tree={story.branches} developments={story.developments} currentId={currentId} />
      </details>
      <a href={`/trending/${story.canonical_slug ?? slug}`} className="rule-live block py-3 font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
        The whole story, every development →
      </a>
    </div>
  );
}
