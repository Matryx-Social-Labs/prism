"use client";

import { ChevronDown, Corner } from "@/components/icons";

import Link from "next/link";
import { useMemo, useState } from "react";

import { spanDays } from "@/lib/spine";
import type { BranchNode, BranchTreeData, StoryDevelopment } from "@/lib/api";

// The storyline branch tree (Prism Mobile.dc.html, screen 2).
//
// partition.py has been writing branch_parent_id / off_spine every run since the
// storyline partitioner shipped, and until now nothing read them: the page
// rendered a flat timeline that threw the structure away.
//
// The design's call, and the reason this doesn't look like a drawn tree: in
// TRUNK — the default — it IS the flat timeline. Root, then the longest on-spine
// chain, one line each, satellites hidden. A reader who doesn't care about
// structure sees exactly the old page plus one counted line. No arborescence, no
// horizontal scroll. Branches stay collapsed in place at their parent's row as a
// single 44px "↳ 4 developments" tap row; expanding indents them under a
// hairline. Depth 2 gets indent only, no connector. ALL is a deliberate detour
// that adds satellites on a dashed rule with a SATELLITE tag.
//
// That degradation matters more than it sounds: most storylines here are 2–4
// developments deep, so for them the tree correctly renders as the plain list it
// always was, and the structure only appears when there is structure.

type Props = {
  tree: BranchTreeData;
  developments: StoryDevelopment[];
  /** The development the reader arrived on, if any — carries the lens hue. */
  currentId?: string | null;
  /** Open on ALL rather than the trunk: the route page, where the whole story is the point. */
  defaultAll?: boolean;
  /** The counted shape line above the list; off where the page's strip already prints it. */
  readout?: boolean;
};

type Row = {
  key: string;
  kind: "dev" | "branch";
  title: string;
  /** The mono date column: a day ("16 SEP"), or a branch's span ("12-23 JUL"). */
  date: string;
  /** A reading-voice tag after the title: First, You are here, Also reported. */
  tag: string | null;
  /** The development's sources, when the payload counts them. */
  sources: number | null;
  depth: number;
  /** Rail style for the left connector: none at depth 0, hairline for a branch. */
  rail: "none" | "solid" | "strong" | "dashed";
  muted: boolean;
  bold: boolean;
  current: boolean;
  satellite: boolean;
  onTap?: () => void;
  /** Development rows navigate; the branch toggle and the current row don't. */
  href?: string;
};

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function stamp(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : `${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]}`;
}

/** "11–23 JUL" for a set of developments; the design's collapsed-branch meta. */
function span(devs: StoryDevelopment[]): string {
  const stamps = devs.map((d) => d.occurred_at).filter((s): s is string => !!s).sort();
  if (!stamps.length) return "";
  const a = stamp(stamps[0]);
  const b = stamp(stamps[stamps.length - 1]);
  if (a === b) return a;
  // Same month reads better collapsed: "11-23 JUL", not "11 JUL - 23 JUL".
  const [ad, am] = a.split(" ");
  const [bd, bm] = b.split(" ");
  return am === bm ? `${ad}-${bd} ${bm}` : `${a} - ${b}`;
}


export function BranchTree({ tree, developments, currentId = null, defaultAll = false, readout = true }: Props) {
  const [showAll, setShowAll] = useState(defaultAll);
  const [openBranch, setOpenBranch] = useState<string | null>(null);

  const byId = useMemo(() => new Map(developments.map((d) => [d.id, d])), [developments]);

  const { spine, branchAt, satelliteAt, onSpineCount } = useMemo(() => {
    const kids = new Map<string, BranchNode[]>();
    for (const n of tree.nodes) {
      if (!n.parent_id) continue;
      const list = kids.get(n.parent_id) ?? [];
      list.push(n);
      kids.set(n.parent_id, list);
    }
    // Sort siblings before walking. Several children usually tie for "longest
    // chain" (they are all leaves), and without this the one promoted onto the
    // spine is whatever order the rows arrived in — so the same storyline could
    // render a different spine between requests. Earliest first: the footer
    // promises every development attaches forward in time.
    const order = (n: BranchNode) => byId.get(n.id)?.occurred_at ?? "";
    for (const list of kids.values()) {
      list.sort((x, y) => order(x).localeCompare(order(y)) || x.id.localeCompare(y.id));
    }

    // The spine is the longest chain of on-spine nodes from the root. Memoised
    // depth-first — a storyline can carry a few hundred developments and the
    // naive recursion re-walks shared tails.
    const best = new Map<string, string[]>();
    const chain = (id: string, seen: Set<string>): string[] => {
      const hit = best.get(id);
      if (hit) return hit;
      // Return EMPTY, not [id]: handing back a node already on the current path
      // stops the recursion but splices that node into the spine a second time,
      // so it renders twice with a duplicate React key. A cycle contributes
      // nothing to the chain.
      if (seen.has(id)) return [];
      seen.add(id);
      let longest: string[] = [];
      for (const c of kids.get(id) ?? []) {
        if (c.off_spine) continue;
        const sub = chain(c.id, seen);
        if (sub.length > longest.length) longest = sub;
      }
      seen.delete(id);
      const path = [id, ...longest];
      best.set(id, path);
      return path;
    };

    const spineIds = tree.nodes.length ? chain(tree.root_id, new Set()) : [];
    const onSpine = new Set(spineIds);

    // Anything hanging off a spine node that isn't itself on the spine is a
    // branch; off-spine nodes are satellites and only appear in ALL.
    const branchAt = new Map<string, BranchNode[]>();
    const satelliteAt = new Map<string, BranchNode[]>();
    for (const id of spineIds) {
      const rest = (kids.get(id) ?? []).filter((c) => !onSpine.has(c.id));
      const b = rest.filter((c) => !c.off_spine);
      const s = rest.filter((c) => c.off_spine);
      if (b.length) branchAt.set(id, b);
      if (s.length) satelliteAt.set(id, s);
    }
    // Orphans the frozen member set cut loose re-attach at the root, so they are
    // already parentless; surface them rather than dropping developments the
    // timeline is listing anyway.
    const orphans = tree.nodes.filter((n) => !n.parent_id && n.id !== tree.root_id);
    if (orphans.length) {
      branchAt.set(tree.root_id, [...(branchAt.get(tree.root_id) ?? []), ...orphans.filter((o) => !o.off_spine)]);
      const s = orphans.filter((o) => o.off_spine);
      if (s.length) satelliteAt.set(tree.root_id, [...(satelliteAt.get(tree.root_id) ?? []), ...s]);
    }

    return { spine: spineIds, branchAt, satelliteAt, onSpineCount: spineIds.length };
  }, [tree, byId]);

  const rows: Row[] = [];
  for (const id of spine) {
    const dev = byId.get(id);
    const isRoot = id === tree.root_id;
    rows.push({
      key: id,
      kind: "dev",
      title: dev?.title ?? "Untitled development",
      date: stamp(dev?.occurred_at ?? null),
      tag: isRoot ? "First" : id === currentId ? "You are here" : null,
      sources: dev?.source_count ?? null,
      depth: 0,
      rail: "none",
      muted: false,
      bold: true,
      current: id === currentId,
      satellite: false,
      href: id === currentId ? undefined : `/story/${id}`,
    });

    const branch = branchAt.get(id);
    if (branch?.length) {
      const open = openBranch === id;
      const devs = branch.map((b) => byId.get(b.id)).filter((d): d is StoryDevelopment => !!d);
      rows.push({
        key: `${id}:branch`,
        kind: "branch",
        title: `${branch.length} development${branch.length === 1 ? "" : "s"}`,
        date: span(devs),
        tag: null,
        sources: null,
        depth: 1,
        rail: open ? "strong" : "solid",
        muted: !open,
        bold: open,
        current: false,
        satellite: false,
        onTap: () => setOpenBranch(open ? null : id),
      });
      if (open) {
        for (const child of branch) {
          const cd = byId.get(child.id);
          const deep = child.depth >= 2;
          rows.push({
            key: child.id,
            kind: "dev",
            title: cd?.title ?? "Untitled development",
            date: stamp(cd?.occurred_at ?? null),
            tag: child.id === currentId ? "You are here" : null,
            sources: cd?.source_count ?? null,
            // Depth 2 gets indent only, no connector — the design is explicit
            // that a second rail reads as a drawn tree, which mobile refuses.
            depth: deep ? 2 : 1,
            rail: deep ? "none" : "strong",
            muted: deep,
            bold: false,
            current: child.id === currentId,
            satellite: false,
            href: child.id === currentId ? undefined : `/story/${child.id}`,
          });
        }
      }
    }

    if (showAll) {
      for (const sat of satelliteAt.get(id) ?? []) {
        const sd = byId.get(sat.id);
        rows.push({
          key: sat.id,
          kind: "dev",
          title: sd?.title ?? "Untitled development",
          date: stamp(sd?.occurred_at ?? null),
          tag: "Also reported",
          sources: sd?.source_count ?? null,
          depth: 1,
          rail: "dashed",
          muted: true,
          bold: false,
          current: sat.id === currentId,
          satellite: true,
          href: sat.id === currentId ? undefined : `/story/${sat.id}`,
        });
      }
    }
  }

  const { developments: n, branches: b, satellites: sat } = tree.shape;
  // Counted, never summarised — the readout prints what the partitioner
  // recorded, plus the span in days from the developments' own dates. The
  // partitioner's max_depth is a fact too, but a reader has no use for it;
  // "9 DAYS" is what the reservation chart would print.
  const days = spanDays(developments);
  const shapeLine = [
    `${n} DEVELOPMENT${n === 1 ? "" : "S"}`,
    `${b} BRANCHED OFF`,
    `${sat} ALSO REPORTED`,
    ...(days != null ? [`${days} DAY${days === 1 ? "" : "S"}`] : []),
  ].join(" · ");

  return (
    <section aria-label="Storyline structure">
      {readout && <p className="p-count mb-3 whitespace-normal">{shapeLine}</p>}

      {/* Design System v2 · structure/BranchTree: the main line, or everything. */}
      <div className="p-seg mb-2" role="tablist" aria-label="Show">
        {([["Main line", false, onSpineCount], ["All", true, tree.nodes.length]] as const).map(([label, all, count]) => (
          <button key={label} type="button" role="tab" aria-selected={showAll === all} onClick={() => setShowAll(all)}>
            {label}{" "}
            <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{count}</span>
          </button>
        ))}
      </div>

      <ol className="border-b" style={{ borderColor: "var(--line)" }}>
        {rows.map((r) => {
          const railColor = r.rail === "solid" ? "var(--line)" : "var(--line-strong)";
          // A row is one of three tags — a link to its development, the branch
          // toggle, or an inert row for the one you're already on — so the body
          // is built once and each tag gets it as children. A single dynamic
          // <Tag> would be shorter, but TS collapses the props of a union-typed
          // tag to `never`, and the escape hatch is a cast that would silence
          // real prop errors on all three.
          const shared = {
            className: "flex w-full min-h-[44px] items-baseline gap-2.5 py-2.5 pr-1 text-left",
            style: {
              paddingLeft: r.rail === "none" ? 0 : 12,
              borderLeft: r.rail === "none" ? undefined : `1.5px ${r.rail === "dashed" ? "dashed" : "solid"} ${railColor}`,
            },
          };
          const body = (
            <>
              <span className="w-[64px] shrink-0 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{r.date}</span>
              <span className="min-w-0 flex-1" style={{ font: `${r.bold ? 600 : 500} 14.5px/1.4 var(--font-read)`, color: r.muted ? "var(--ink-2)" : "var(--ink)", textWrap: "pretty" }}>
                {r.kind === "branch" && (
                  <span className="mr-1.5 inline-flex translate-y-[2px]" data-open={r.bold ? "true" : "false"}>
                    {r.bold ? <ChevronDown /> : <Corner />}
                  </span>
                )}
                {r.title}
                {r.tag && <span className="p-eyebrow ml-2 whitespace-nowrap">{r.tag}</span>}
              </span>
              {r.sources != null && <span className="p-count shrink-0">{r.sources} {r.sources === 1 ? "source" : "sources"}</span>}
            </>
          );
          return (
            <li
              key={r.key}
              className="border-t"
              style={{
                borderColor: "var(--line)",
                paddingLeft: r.depth === 0 ? 0 : r.depth === 2 ? 36 : 22,
                background: r.current || (r.kind === "branch" && r.bold) ? "var(--sunken)" : "transparent",
              }}
            >
              {r.href ? (
                <Link href={r.href} {...shared}>
                  {body}
                </Link>
              ) : r.onTap ? (
                <button
                  type="button"
                  onClick={r.onTap}
                  // Without this the name concatenates to "2 developments12–23 JUL".
                  aria-label={r.date ? `${r.title}, ${r.date}` : r.title}
                  aria-expanded={r.bold}
                  {...shared}
                >
                  {body}
                </button>
              ) : (
                <div {...shared}>{body}</div>
              )}
            </li>
          );
        })}
      </ol>

      <p className="max-w-[44ch] pb-2 pt-3" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
        The first row is the most-reported development; every other follows it in time
      </p>
    </section>
  );
}
