import type { BranchTreeData, StoryDevelopment } from "@/lib/api";

/**
 * How many developments the trunk of a story has: the longest chain of
 * on-spine nodes from the root, the same measure BranchTree prints as
 * "N ON THE SPINE". A plain module so a server component can ask before it
 * decides whether a route is worth showing (a route with one station shows
 * no route). Sibling order does not change the length, so none is imposed.
 */
export function spineLength(tree: BranchTreeData | null | undefined): number {
  if (!tree || tree.nodes.length === 0) return 0;
  const kids = new Map<string, string[]>();
  for (const n of tree.nodes) {
    if (!n.parent_id || n.off_spine) continue;
    kids.set(n.parent_id, [...(kids.get(n.parent_id) ?? []), n.id]);
  }
  const best = new Map<string, number>();
  const chain = (id: string, seen: Set<string>): number => {
    const hit = best.get(id);
    if (hit != null) return hit;
    if (seen.has(id)) return 0; // a cycle contributes nothing
    seen.add(id);
    let longest = 0;
    for (const c of kids.get(id) ?? []) longest = Math.max(longest, chain(c, seen));
    seen.delete(id);
    best.set(id, 1 + longest);
    return 1 + longest;
  };
  return chain(tree.root_id, new Set());
}

/** Calendar days from the first dated development to the last, inclusive; null when nothing is dated. */
export function spanDays(devs: StoryDevelopment[]): number | null {
  const ts = devs.map((d) => Date.parse(d.occurred_at ?? "")).filter((t) => !Number.isNaN(t));
  if (!ts.length) return null;
  return Math.floor((Math.max(...ts) - Math.min(...ts)) / 86_400_000) + 1;
}
