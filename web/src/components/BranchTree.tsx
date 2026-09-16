"use client";

import { ChevronDown, Corner } from "@/components/icons";

import Link from "next/link";
import { useMemo, useState } from "react";

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
};

type Row = {
  key: string;
  kind: "dev" | "branch";
  title: string;
  meta: string;
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

/** Calendar days from the first dated development to the last, inclusive; null when nothing is dated. */
export function spanDays(devs: StoryDevelopment[]): number | null {
  const ts = devs.map((d) => Date.parse(d.occurred_at ?? "")).filter((t) => !Number.isNaN(t));
  if (!ts.length) return null;
  return Math.floor((Math.max(...ts) - Math.min(...ts)) / 86_400_000) + 1;
}

export function BranchTree({ tree, developments, currentId = null }: Props) {
  const [showAll, setShowAll] = useState(false);
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
      meta: [stamp(dev?.occurred_at ?? null), isRoot ? "ROOT" : id === currentId ? "YOU ARE HERE" : ""]
        .filter(Boolean)
        .join(" · "),
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
        meta: span(devs),
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
            meta: [stamp(cd?.occurred_at ?? null), deep ? "DEPTH 2" : ""].filter(Boolean).join(" · "),
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
          meta: [stamp(sd?.occurred_at ?? null), "SATELLITE"].filter(Boolean).join(" · "),
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

  const shown = rows.filter((r) => r.kind === "dev").length;
  const { developments: n, branches: b, satellites: sat } = tree.shape;
  // Counted, never summarised — the readout prints what the partitioner
  // recorded, plus the span in days from the developments' own dates. The
  // partitioner's max_depth is a fact too, but a reader has no use for it;
  // "9 DAYS" is what the reservation chart would print.
  const days = spanDays(developments);
  const shapeLine = [
    `${n} DEVELOPMENT${n === 1 ? "" : "S"}`,
    `${b} BRANCH${b === 1 ? "" : "ES"}`,
    `${sat} SATELLITE${sat === 1 ? "" : "S"}`,
    ...(days != null ? [`${days} DAY${days === 1 ? "" : "S"}`] : []),
  ].join(" · ");

  return (
    <section aria-label="Storyline structure">
      <div
        className="font-mono text-[11px] uppercase leading-[1.7] tracking-[0.06em]"
        style={{ color: "var(--ink-muted)" }}
      >
        {shapeLine}
      </div>

      <div
        className="sticky top-0 z-20 mt-3 flex items-center gap-2.5 border-y px-1 py-2"
        style={{ borderColor: "var(--line)", background: "var(--bg)" }}
      >
        <span className="font-mono text-[11px] tracking-[0.1em]" style={{ color: "var(--ink-faint)" }}>
          {showAll ? `ALL · ${shown} SHOWN` : `TRUNK · ${onSpineCount} ON THE SPINE`}
        </span>
        <div className="ml-auto flex gap-4">
          {([["TRUNK", false], ["ALL", true]] as const).map(([label, all]) => (
            <button
              key={label}
              onClick={() => setShowAll(all)}
              aria-pressed={showAll === all}
              className="flex h-9 items-center border-b-2 px-1 font-mono text-[11px] tracking-[0.1em]"
              style={{
                borderColor: showAll === all ? "var(--ink)" : "transparent",
                color: showAll === all ? "var(--ink)" : "var(--ink-muted)",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div>
        {rows.map((r) => {
          const railColor =
            r.rail === "strong" ? "var(--line-strong)" : r.rail === "dashed" ? "var(--line-strong)" : "var(--line)";
          // A row is one of three tags — a link to its development, the branch
          // toggle, or an inert row for the one you're already on — so the body
          // is built once and each tag gets it as children. A single dynamic
          // <Tag> would be shorter, but TS collapses the props of a union-typed
          // tag to `never`, and the escape hatch is a cast that would silence
          // real prop errors on all three.
          const shared = {
            className: "flex w-full min-h-[44px] items-start gap-[11px] py-3 pr-1 text-left",
            style: {
              paddingLeft: r.rail === "none" ? 0 : 14,
              borderLeft:
                r.rail === "none" ? undefined : `1px ${r.rail === "dashed" ? "dashed" : "solid"} ${railColor}`,
            },
          };
          const body = (
            <>
                {r.kind === "dev" ? (
                  <span
                    aria-hidden
                    className="mt-[5px] block h-[7px] w-[7px] flex-none"
                    style={{
                      background: r.current
                        ? "var(--lens-general)"
                        : r.satellite
                          ? "var(--ink-faint)"
                          : r.depth === 0
                            ? "var(--ink)"
                            : "var(--ink-muted)",
                      boxShadow: r.current ? "0 0 0 3px var(--lens-general-bg)" : undefined,
                    }}
                  />
                ) : null}
                <span className="min-w-0 flex-1">
                  <span
                    className="block text-[13.5px] leading-[1.4]"
                    style={{
                      fontWeight: r.bold ? 600 : 400,
                      color: r.muted ? "var(--ink-muted)" : "var(--ink)",
                      textWrap: "pretty",
                    }}
                  >
                    {r.kind === "branch" && (
                      <span className="mr-1.5 inline-flex translate-y-[2px]" data-open={r.bold ? "true" : "false"}>
                        {r.bold ? <ChevronDown /> : <Corner />}
                      </span>
                    )}
                    {r.title}
                  </span>
                  {r.meta && (
                    <span
                      className="font-mono text-[11px] tracking-[0.06em]"
                      style={{ color: "var(--ink-faint)" }}
                    >
                      {r.meta}
                    </span>
                  )}
                </span>
            </>
          );
          return (
            <div
              key={r.key}
              className="border-b"
              style={{
                borderColor: "var(--line)",
                paddingLeft: r.depth === 0 ? 0 : r.depth === 2 ? 36 : 22,
                background: r.current
                  ? "var(--bg-sunken)"
                  : r.kind === "branch" && r.bold
                    ? "var(--bg-sunken)"
                    : "transparent",
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
                  aria-label={r.meta ? `${r.title}, ${r.meta}` : r.title}
                  aria-expanded={r.bold}
                  {...shared}
                >
                  {body}
                </button>
              ) : (
                <div {...shared}>{body}</div>
              )}
            </div>
          );
        })}
      </div>

      <p
        className="max-w-[40em] px-1 pb-5 pt-3.5 font-mono text-[12px] leading-[1.7] tracking-[0.02em]"
        style={{ color: "var(--ink-faint)" }}
      >
        Root is the most-corroborated development; every other attaches forward in time
      </p>
    </section>
  );
}
