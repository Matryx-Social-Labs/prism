"use client";

import { useEffect, useState } from "react";
import { BranchTree } from "@/components/BranchTree";
import { ChevronDown } from "@/components/icons";
import { RouteMap } from "@/components/RouteMap";
import { StoryTimeline } from "@/components/StoryTimeline";
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
      <div className="grid gap-2" aria-busy="true">
        <span className="p-count">Loading the story…</span>
        <span className="p-skel h-3 w-[70%]" />
        <span className="p-skel h-3 w-[55%]" />
      </div>
    );
  }
  if (!story || story.developments.length < 2) return null;

  if (story.boundary_status !== "verified") {
    return (
      <div>
        <StoryTimeline story={{ developments: story.developments, cast: [] }} mode="related" />
        <a href={`/trending/${story.canonical_slug ?? slug}`} className="p-link mt-2.5 inline-flex min-h-[44px] items-center text-[14.5px]">
          Open this coverage group →
        </a>
      </div>
    );
  }

  if (!story.branches || story.branches.nodes.length < 2) return null;

  return (
    <div>
      <RouteMap tree={story.branches} developments={story.developments} currentId={currentId} compact />
      <details className="group mt-2 border-t" style={{ borderColor: "var(--line)" }}>
        <summary className="flex min-h-[44px] cursor-pointer list-none items-center gap-2" style={{ font: "600 13.5px/1.3 var(--font-read)", color: "var(--ink-2)" }}>
          <ChevronDown className="transition-transform group-open:rotate-180" />
          All developments
        </summary>
        <BranchTree tree={story.branches} developments={story.developments} currentId={currentId} />
      </details>
      <a href={`/trending/${story.canonical_slug ?? slug}`} className="p-link inline-flex min-h-[44px] items-center text-[14.5px]">
        The whole story →
      </a>
    </div>
  );
}
