"use client";

/**
 * Every founder link, newest first, with what its visits did in the period:
 * visits (the first page of a visit that came by it), then, in the same tab, a
 * second story, a sign-in asked for, an account made, the Plus page, the
 * weekly email. Counts, never who; below 30 they are only counts. A row opens
 * its visits day by day. Archive hides a link from this list; it keeps working.
 */

import { useState } from "react";

import { ChartPanel } from "@/components/admin/charts/ChartPanel";
import { dayLabel } from "@/components/admin/charts/format";
import { TrendChart, trendTable } from "@/components/admin/charts/TrendChart";
import { Act, Badge, FilterSwitch, SearchBox, matches } from "@/components/admin/ui";
import { Quiet } from "@/components/admin/AdminShell";
import type { CountedLink, LinkGoal, LinksPayload } from "@/lib/admin";
import { PLATFORM_LABEL, type Platform } from "@/lib/shareLinks";

type Show = "live" | "archived" | "all";
const SHOW_WORD: Record<Show, string> = { live: "Live", archived: "Archived", all: "All" };
/** The steps after a visit, in the order a reader takes them, as the table heads them. */
export const GOAL_HEAD: ReadonlyArray<[LinkGoal, string]> = [
  ["read2", "Read on"], ["signin", "Sign-in"], ["account", "Account"], ["plus", "Plus page"], ["digest", "Email"],
];
export const platformName = (p: string) => PLATFORM_LABEL[p as Platform] ?? p;
const n = (v: number) => v.toLocaleString("en-IN");

export function LinksTable({ data, onArchive, busy }: { data: LinksPayload; onArchive: (code: string, archived: boolean) => void; busy: string | null }) {
  const [show, setShow] = useState<Show>("live");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const counts: Record<Show, number> = {
    live: data.links.filter((l) => !l.archived_at).length,
    archived: data.links.filter((l) => l.archived_at).length,
    all: data.links.length,
  };
  const rows = data.links.filter(
    (l) => (show === "all" || (show === "live") === !l.archived_at) && matches(q, l.title, l.path, l.code, l.platform, l.campaign, l.note, l.created_by),
  );
  const chosen = data.links.find((l) => l.code === open) ?? null;

  if (data.links.length === 0) return <Quiet>No links yet. The first one you make above appears here with its counts.</Quiet>;
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <FilterSwitch label="Which links" value={show} onChange={setShow}
          options={(Object.keys(SHOW_WORD) as Show[]).map((v) => ({ value: v, label: SHOW_WORD[v], count: counts[v] }))} />
        <SearchBox value={q} onChange={setQ} placeholder="Page, code, platform, campaign, note" />
      </div>
      <div className="min-w-0 overflow-x-auto overflow-y-hidden overscroll-x-contain">
        <table className="p-table">
          <thead>
            <tr>
              <th scope="col">Link</th>
              <th scope="col">Where</th>
              <th scope="col" className="num">Visits</th>
              {GOAL_HEAD.map(([g, head]) => <th key={g} scope="col" className="num">{head}</th>)}
              <th scope="col" className="num">Made</th>
              <th scope="col"><span className="p-sr">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => <Row key={l.code} l={l} open={open === l.code} onOpen={() => setOpen(open === l.code ? null : l.code)} onArchive={onArchive} busy={busy === l.code} />)}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <Quiet>No link matches.</Quiet>}
      {chosen && (
        <ChartPanel
          title={`Visits by day · ${chosen.code}`}
          source="usage_daily · founder links · the first page of each visit that carried this code"
          note="Days before the link was made are not drawn. A platform's own click count is higher: it counts bots, link previews and readers without JavaScript."
          empty={chosen.series.some((v) => v !== null) ? null : "Made after this period."}
          table={trendTable(chosen.series, null, data.range.start, "Visits")}
        >
          <TrendChart series={chosen.series} start={data.range.start} label="Visits" />
        </ChartPanel>
      )}
    </div>
  );
}

function Row({ l, open, onOpen, onArchive, busy }: { l: CountedLink; open: boolean; onOpen: () => void; onArchive: (code: string, archived: boolean) => void; busy: boolean }) {
  return (
    <tr aria-selected={open}>
      <td>
        <button type="button" className="grid min-w-[220px] gap-0.5 text-left" onClick={onOpen} aria-expanded={open} aria-label={`Visits by day for ${l.code}`}>
          <span className="font-mono text-[12px]" style={{ color: "var(--ink)" }}>{l.code}</span>
          <span className="text-[14px] font-medium leading-[1.35]" style={{ color: "var(--ink)" }}>{l.title || l.path}</span>
          <span className="font-mono text-[11.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink-3)" }}>{l.path}</span>
        </button>
      </td>
      <td>
        <span className="grid gap-1">
          <span className="min-w-[120px] text-[14px] font-medium">{platformName(l.platform)}</span>
          <span className="flex flex-wrap gap-1">
            <Badge>{l.medium}</Badge>
            {l.campaign ? <Badge tone="ink">{l.campaign}</Badge> : null}
            {l.archived_at ? <Badge tone="dashed">archived</Badge> : null}
          </span>
          {l.note && <span className="text-[12.5px]" style={{ color: "var(--ink-2)" }}>{l.note}</span>}
        </span>
      </td>
      <td className="num">{n(l.visits)}</td>
      {GOAL_HEAD.map(([g]) => <td key={g} className="num">{n(l.goals[g] ?? 0)}</td>)}
      <td className="num">
        <span className="grid">
          <span>{dayLabel(l.created_at)}</span>
          <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)", textTransform: "none" }}>{l.created_by}</span>
        </span>
      </td>
      <td>
        <span className="flex gap-1">
          <Act onClick={() => void navigator.clipboard?.writeText(l.short_url)}>Copy</Act>
          <Act onClick={() => onArchive(l.code, !l.archived_at)} disabled={busy}>{l.archived_at ? "Restore" : "Archive"}</Act>
        </span>
      </td>
    </tr>
  );
}
