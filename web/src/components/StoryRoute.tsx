"use client";

import { useEffect, useState } from "react";
import { BranchTree } from "@/components/BranchTree";
import { fetchTrendingStory, type TrendingStoryDetail } from "@/lib/api";

/**
 * The route: the spine of the story this event belongs to, as a route map.
 *
 * The event payload carries no arc — /trending/{slug} owns it, built from the
 * story's frozen member set, so the ticket and the share page can never
 * disagree about which developments exist. The ticket carries the slug and
 * asks the owner. No slug, no section: a story with one development has no
 * route to show, and an older payload simply has none. A storyline that
 * predates the partition run carries no tree and shows nothing here either —
 * /trending/{slug} still renders its flat timeline.
 */
export function StoryRoute({ slug, currentId }: { slug: string; currentId: string }) {
  const [story, setStory] = useState<TrendingStoryDetail | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    fetchTrendingStory(slug).then((s) => {
      if (!cancelled) setStory(s);
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (story === undefined) {
    return (
      <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }} aria-busy="true">
        Printing the route…
      </p>
    );
  }
  if (!story?.branches || story.branches.nodes.length < 2) return null;

  return <BranchTree tree={story.branches} developments={story.developments} currentId={currentId} />;
}
