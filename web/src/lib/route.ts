import type { BranchTreeData, StoryDevelopment } from "@/lib/api";

/**
 * The shape of a story as the route map draws it, derived from the branch
 * tree the partitioner recorded (branch_parent_id + off_spine per member):
 *
 * - the MAIN LINE: the longest chain of on-spine nodes from the root, the
 *   same measure BranchTree prints as "N ON THE SPINE" (lib/spine.ts);
 * - a BRANCH: an on-spine child of a main-line station that is not on the
 *   trunk, with everything that grew under it, in time order; two stops or
 *   fewer;
 * - a BRANCH LINE: a branch of three stops or more, a sub-spine that grew
 *   its own stations;
 * - SATELLITES: off-spine members, reported but not on any line.
 *
 * Every node has a parent in the record (the best strictly-earlier member),
 * on-spine or not, so an on-spine node can hang from a satellite; the map
 * reads through satellites to the nearest on-spine ancestor, because a line
 * cannot leave a station that is not on a line. Members the frozen set cut
 * loose (no parent, not the root) are branches from the root, as BranchTree
 * lists them, never the trunk: the record did not say they lead anywhere.
 *
 * Sibling order is earliest first, so the same story draws the same map on
 * every request. Nothing here is inferred: a station is a development the
 * record holds, a line is a parent link the partitioner wrote.
 */
export type Station = StoryDevelopment & { day: number };
export type Line = { kind: "branch" | "line"; from: string; stations: Station[] };
export type RouteShape = { trunk: Station[]; lines: Line[]; satellites: Station[]; day0: string | null; days: number };

export function routeShape(tree: BranchTreeData, developments: StoryDevelopment[]): RouteShape {
  const byId = new Map(developments.map((d) => [d.id, d]));
  const t0 = Math.min(...developments.map((d) => Date.parse(d.occurred_at ?? "") || Infinity));
  const day = (d: StoryDevelopment) => (Number.isFinite(t0) && d.occurred_at ? Math.max(0, Math.floor((Date.parse(d.occurred_at) - t0) / 86_400_000)) : 0);
  const station = (id: string): Station | null => { const d = byId.get(id); return d ? { ...d, day: day(d) } : null; };
  const order = (id: string) => byId.get(id)?.occurred_at ?? "";
  const byTime = (a: string, b: string) => order(a).localeCompare(order(b)) || a.localeCompare(b);

  const node = new Map(tree.nodes.map((n) => [n.id, n]));
  const onSpine = (id: string) => id === tree.root_id || node.get(id)?.off_spine === false;
  // The nearest on-spine ancestor, reading through satellites; a cycle or a
  // parent outside the record ends the walk.
  const anchor = (id: string): string | null => {
    const seen = new Set<string>([id]);
    let p = node.get(id)?.parent_id ?? null;
    while (p && node.has(p) && !onSpine(p) && !seen.has(p)) { seen.add(p); p = node.get(p)?.parent_id ?? null; }
    return p && node.has(p) ? p : null;
  };
  const kids = new Map<string, string[]>();
  const orphans: string[] = [];
  for (const n of tree.nodes) {
    if (n.id === tree.root_id || !onSpine(n.id)) continue;
    const a = anchor(n.id);
    if (a) kids.set(a, [...(kids.get(a) ?? []), n.id]); else orphans.push(n.id);
  }
  for (const list of kids.values()) list.sort(byTime);

  // Longest chain from a node, memoised; a cycle contributes nothing.
  const best = new Map<string, string[]>();
  const chain = (id: string, seen: Set<string>): string[] => {
    const hit = best.get(id); if (hit) return hit;
    if (seen.has(id)) return [];
    seen.add(id);
    let longest: string[] = [];
    for (const c of kids.get(id) ?? []) { const sub = chain(c, seen); if (sub.length > longest.length) longest = sub; }
    seen.delete(id);
    const path = [id, ...longest]; best.set(id, path); return path;
  };
  const subtree = (id: string, seen = new Set<string>()): string[] => {
    if (seen.has(id)) return [];
    seen.add(id);
    return [id, ...(kids.get(id) ?? []).flatMap((c) => subtree(c, seen))];
  };

  const trunkIds = tree.nodes.length ? chain(tree.root_id, new Set()) : [];
  const onTrunk = new Set(trunkIds);
  const lines: Line[] = [];
  const line = (from: string, ids: string[]) => {
    const stations = ids.map(station).filter((s): s is Station => s !== null);
    if (stations.length) lines.push({ kind: stations.length >= 3 ? "line" : "branch", from, stations });
  };
  for (const id of trunkIds) {
    for (const c of kids.get(id) ?? []) if (!onTrunk.has(c)) line(id, subtree(c).sort(byTime));
  }
  for (const o of orphans.sort(byTime)) if (trunkIds.length) line(tree.root_id, subtree(o).sort(byTime));

  const trunk = trunkIds.map(station).filter((s): s is Station => s !== null);
  const satellites = tree.nodes.filter((n) => n.id !== tree.root_id && !onSpine(n.id)).map((n) => station(n.id)).filter((s): s is Station => s !== null)
    .sort((a, b) => a.day - b.day || a.id.localeCompare(b.id));
  const days = Math.max(1, ...[...trunk, ...lines.flatMap((l) => l.stations), ...satellites].map((s) => s.day)) + 1;
  return { trunk, lines, satellites, day0: Number.isFinite(t0) ? new Date(t0).toISOString() : null, days };
}
