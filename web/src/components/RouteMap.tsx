"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { BranchTreeData, StoryDevelopment } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { routeShape, type Line, type Station } from "@/lib/route";

/**
 * The route map: a story drawn as a rail map (founder decision, 2026-09-17,
 * direction A). Topological, not to scale, so it stays legible at twenty-five
 * developments. The main line is thick; a branch diverges upward on a dashed
 * rail; a branch line diverges downward on its own solid rail with its own
 * stations; satellites float beneath on their day. Identity is line form,
 * never hue: the only ink is ink. The station you are on is filled and,
 * unless motion is reduced, carries a slow halo.
 *
 * Every station is a 32px hit target with a tooltip on hover and focus and
 * the same details on tap in a card beneath the map; arrow keys move along
 * the line. The list under the map is the table view, so nothing here is
 * only reachable by pointer. The line draws itself in once (700ms); under
 * reduced motion it is simply there.
 */
type Props = {
  tree: BranchTreeData;
  developments: StoryDevelopment[];
  currentId?: string | null;
  /** The ticket's form: this station and its two neighbours either way, no satellites. */
  compact?: boolean;
  /** Where a station's card links to; the current station links nowhere. */
  href?: (s: Station) => string;
};

const GAP = { full: 230, compact: 190 };
// Five satellites and their labels fit the route page's 860px column.
const SAT_GAP = 150;

function short(t: string, max = 24, lines = 2): string[] {
  const words = t.split(" "); const out: string[] = []; let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length > max && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim();
    if (out.length === lines) break;
  }
  if (out.length < lines && cur) out.push(cur);
  if (out.length === lines && words.join(" ").length > out.join(" ").length) out[lines - 1] = out[lines - 1].replace(/\s*\S*$/, "") + "…";
  return out;
}

export function RouteMap({ tree, developments, currentId = null, compact = false, href = (s) => `/story/${s.id}` }: Props) {
  const shape = useMemo(() => routeShape(tree, developments), [tree, developments]);
  const [picked, setPicked] = useState<Station | null>(null);
  const [hover, setHover] = useState<{ s: Station; x: number; y: number } | null>(null);
  const [drawn, setDrawn] = useState(false);
  // A phone reads the map top to bottom, labels beside the stations, no
  // sideways panning; from 640px it reads left to right like a rail map.
  // Starts in the wide form on both server and client so hydration matches;
  // the effect below switches a phone to the tall form before first paint.
  const [vertical, setVertical] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => { const t = setTimeout(() => setDrawn(true), 10); return () => clearTimeout(t); }, []);
  useLayoutEffect(() => {
    const mq = window.matchMedia("(min-width: 640px)");
    const on = () => setVertical(!mq.matches);
    on(); mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const trunk = useMemo(() => {
    if (!compact || !currentId) return shape.trunk;
    const i = shape.trunk.findIndex((s) => s.id === currentId);
    return i < 0 ? shape.trunk.slice(0, 5) : shape.trunk.filter((_, k) => Math.abs(k - i) <= 2);
  }, [shape, compact, currentId]);
  if (trunk.length === 0) return null;

  const gap = compact ? GAP.compact : GAP.full, x0 = 90, yMain = compact ? 84 : 100;
  const xs = new Map(trunk.map((s, i) => [s.id, x0 + i * gap]));
  const lines = shape.lines.filter((l) => xs.has(l.from));
  // Each line takes the first rail (lane) where its span is clear: two
  // branches leaving one station, or a branch line running past the next
  // station, get their own rail instead of drawing over each other.
  const lane = new Map<Line, number>(); const used = { branch: [] as [number, number][][], line: [] as [number, number][][] };
  for (const l of lines) {
    const fx = xs.get(l.from)!, span: [number, number] = [fx, fx + 40 + (l.stations.length - 1) * 70 + 30];
    const rails = used[l.kind]; let k = rails.findIndex((r) => r.every(([a, b]) => span[1] < a || span[0] > b));
    if (k < 0) { k = rails.length; rails.push([]); }
    rails[k].push(span); lane.set(l, k);
  }
  const upLanes = used.branch.length, downLanes = used.line.length;
  const ySat = yMain + (downLanes ? 84 + (downLanes - 1) * 62 + 86 : 96);
  const reach = Math.max(x0 + gap * (trunk.length - 1) + (compact ? 140 : 320), ...[...used.branch, ...used.line].flat().map(([, b]) => b + 60), compact || !shape.satellites.length ? 0 : x0 + Math.min(5, shape.satellites.length) * SAT_GAP + (shape.satellites.length > 5 ? 100 : 0));
  const W = reach;
  const H = compact ? (downLanes ? 210 + (downLanes - 1) * 62 : 170) : ySat + (shape.satellites.length ? 60 : 10);
  const yTop = upLanes ? -(upLanes - 1) * 48 : 40;

  const onEnter = (s: Station, cx: number, cy: number) => setHover({ s, x: cx, y: cy });
  const station = (s: Station, cx: number, cy: number, cls: string) => {
    const here = s.id === currentId;
    return (
      <g key={s.id}>
        {here && !reduce && <circle cx={cx} cy={cy} r={9} className="rm-halo" />}
        <circle cx={cx} cy={cy} r={here ? 6.5 : 5} className={`rm-stn ${cls}${here ? " rm-here" : ""}`} />
        <circle
          cx={cx} cy={cy} r={16} className="rm-hit" tabIndex={0} role="button"
          aria-label={`${s.title}, ${s.occurred_at ? shortDate(s.occurred_at) : ""}, ${s.source_count ?? 1} sources`}
          onPointerEnter={() => onEnter(s, cx, cy)} onPointerLeave={() => setHover(null)}
          onFocus={() => onEnter(s, cx, cy)} onBlur={() => setHover(null)}
          onClick={() => setPicked(s)} onKeyDown={(e) => { if (e.key === "Enter") setPicked(s); }}
        />
      </g>
    );
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const hits = [...(wrap.current?.querySelectorAll<SVGElement>(".rm-hit") ?? [])];
    const i = hits.indexOf(document.activeElement as SVGElement); if (i < 0) return;
    e.preventDefault(); hits[Math.max(0, Math.min(hits.length - 1, i + (e.key === "ArrowRight" ? 1 : -1)))].focus();
  };

  // The tooltip and the card show the same things; the card also links out.
  const facts = (s: Station) => `${s.occurred_at ? shortDate(s.occurred_at) : ""} · ${s.source_count ?? 1} ${(s.source_count ?? 1) === 1 ? "source" : "sources"}${s.why ? " · " + s.why : ""}`;
  const card = (p: Station) => (
    <div className="rm-card" role="dialog" aria-label={p.title}>
      <span className="font-display text-[40px] leading-[0.9]">{p.source_count ?? 1}</span>
      <span className="mt-2 block font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>{facts(p)}{p.id === currentId ? " · you are here" : ""}</span>
      <b className="mt-1.5 block text-[16px] font-medium leading-[1.35]">{p.title}</b>
      {p.id === currentId ? (
        <span className="mt-3 block font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-muted)" }}>This is the ticket you are on</span>
      ) : (
        <Link href={href(p)} className="mt-3 inline-block font-mono text-[11px] uppercase tracking-[0.06em] underline underline-offset-4">Open the ticket →</Link>
      )}
      <button type="button" className="rm-close" aria-label="Close" onClick={() => setPicked(null)}>✕</button>
    </div>
  );

  if (vertical) {
    // Layout down the page: the main line at x=36; a branch or branch line
    // hangs to the right of the station it left, its stations stacked; the
    // trunk makes room beneath that station. Satellites list at the foot.
    const X = 36, LX = 60, MAXW = 34;
    let y = 34; const pos = new Map<string, number>(); const rows: React.ReactNode[] = [];
    for (const s of trunk) {
      pos.set(s.id, y);
      const here = s.id === currentId;
      const tag = s.id === shape.trunk[0]?.id ? "Root" : s.id === shape.trunk.at(-1)?.id ? "Latest" : here ? "You are here" : null;
      rows.push(
        <g key={s.id}>
          <text x={LX} y={y - 8} className="rm-lab">{s.occurred_at ? shortDate(s.occurred_at) : ""}{tag ? ` · ${tag}` : ""}</text>
          <text x={LX} y={y + 6} className={`rm-ttl${here ? " rm-ttl-here" : ""}`}>
            {short(s.title, MAXW).map((ln, k) => <tspan key={k} x={LX} dy={k ? 13 : 0}>{ln}</tspan>)}
          </text>
          {station(s, X, y, "")}
        </g>,
      );
      let dy = 64;
      for (const l of lines.filter((l) => l.from === s.id)) {
        const up = l.kind === "branch", bx = X + 26, by0 = y + dy;
        rows.push(<path key={`${l.stations[0].id}-rail`} d={`M${X} ${y} C${X} ${y + 14}, ${bx} ${y + 12}, ${bx} ${by0 - 10} V${by0 + (l.stations.length - 1) * 44}`} className={up ? "rm-branch" : "rm-bline"} />);
        rows.push(<text key={`${l.stations[0].id}-k`} x={bx + 16} y={by0 - 18} className="rm-k">{up ? "A branch" : "A branch line"} · {l.stations.length} {l.stations.length === 1 ? "development" : "developments"}</text>);
        l.stations.forEach((bs, i) => {
          const by = by0 + i * 44;
          rows.push(
            <g key={bs.id}>
              <text x={bx + 16} y={by - 6} className={`rm-lab${bs.id === currentId ? " rm-k-here" : ""}`}>{bs.occurred_at ? shortDate(bs.occurred_at) : ""}{bs.id === currentId ? " · You are here" : ""}</text>
              <text x={bx + 16} y={by + 7} className="rm-ttl">{short(bs.title, MAXW - 3, 1)[0]}</text>
              {station(bs, bx, by, up ? "rm-dashed" : "")}
            </g>,
          );
        });
        dy += l.stations.length * 44 + 30;
      }
      y += dy;
    }
    const yEnd = pos.get(trunk.at(-1)!.id)!;
    let ySatV = y + 6;
    const sats: React.ReactNode[] = [];
    if (!compact && shape.satellites.length) {
      sats.push(<text key="sk" x={LX - 24} y={ySatV} className="rm-k rm-k-lc">Also reported, off the main line</text>);
      ySatV += 22;
      for (const s of shape.satellites.slice(0, 5)) {
        sats.push(
          <g key={s.id}>
            <text x={LX} y={ySatV - 6} className="rm-lab">{s.occurred_at ? shortDate(s.occurred_at) : ""}</text>
            <text x={LX} y={ySatV + 7} className="rm-ttl">{short(s.title, MAXW, 1)[0]}</text>
            {station(s, X, ySatV, "rm-dotted")}
          </g>,
        );
        ySatV += 40;
      }
      if (shape.satellites.length > 5) { sats.push(<text key="sm" x={LX} y={ySatV - 8} className="rm-k rm-k-lc">+{shape.satellites.length - 5} more, in the list below</text>); ySatV += 16; }
    }
    const HV = (compact || !shape.satellites.length ? y : ySatV) + 8, WV = 360;
    return (
      <div ref={wrap} className="rm relative" onKeyDown={onKey}>
        <svg viewBox={`0 0 ${WV} ${HV}`} width="100%" height={HV} role="img" aria-label="The route" className={`rm-svg${drawn ? " rm-drawn" : ""}${reduce ? " rm-still" : ""}`} style={{ maxWidth: WV }}>
          <path d={`M${X} ${pos.get(trunk[0].id)} V${yEnd}`} className="rm-main" />
          {rows}
          {sats}
        </svg>
        {hover && (
          <div className="rm-tip" style={{ left: Math.min(hover.x + 16, 80), top: hover.y + 18 }} role="tooltip">
            <b>{hover.s.title}</b>
            <span className="font-mono text-[11px]" style={{ color: "var(--ink-muted)" }}>{facts(hover.s)}</span>
          </div>
        )}
        {picked && card(picked)}
      </div>
    );
  }

  return (
    <div ref={wrap} className="rm relative" onKeyDown={onKey}>
      <div className="overflow-x-auto">
        <svg viewBox={`0 ${yTop} ${W} ${H - yTop}`} width={W} height={H - yTop} role="img" aria-label="The route" className={`rm-svg${drawn ? " rm-drawn" : ""}${reduce ? " rm-still" : ""}`}>
          {/* the main line */}
          <path d={`M${xs.get(trunk[0].id)} ${yMain} H${xs.get(trunk.at(-1)!.id)}`} className="rm-main" />
          {/* branches and branch lines */}
          {lines.map((l) => {
            const fx = xs.get(l.from)!, up = l.kind === "branch", k = lane.get(l) ?? 0, y = up ? yMain - 56 - k * 48 : yMain + 84 + k * 62;
            const bx = l.stations.map((_, i) => fx + 40 + i * 70);
            return (
              <g key={`${l.stations[0].id}-line`}>
                <path d={`M${fx} ${yMain} C${fx + 16} ${yMain}, ${fx + 14} ${y}, ${fx + 40} ${y} H${bx.at(-1)}`} className={up ? "rm-branch" : "rm-bline"} />
                {l.stations.map((s, i) => (
                  <g key={s.id}>
                    <text x={bx[i] + 11} y={y + 4} className={`rm-lab${s.id === currentId ? " rm-k-here" : ""}`}>{s.occurred_at ? shortDate(s.occurred_at) : ""}{s.id === currentId ? " · You are here" : ""}</text>
                    {station(s, bx[i], y, up ? "rm-dashed" : "")}
                  </g>
                ))}
                <text x={bx[0] - 6} y={y + (up ? -16 : 24)} className="rm-k">{up ? "A branch" : "A branch line"} · {l.stations.length} {l.stations.length === 1 ? "development" : "developments"}</text>
              </g>
            );
          })}
          {/* satellites */}
          {!compact && shape.satellites.length > 0 && (
            <g>
              <text x={x0 - 40} y={ySat - 14} className="rm-k rm-k-lc">Also reported, off the main line</text>
              {shape.satellites.length > 5 && <text x={x0 + 5 * SAT_GAP - 30} y={ySat + 4} className="rm-k rm-k-lc">+{shape.satellites.length - 5} more, in the list</text>}
              {shape.satellites.slice(0, 5).map((s, i) => {
                const cx = x0 + i * SAT_GAP;
                return (
                  <g key={s.id}>
                    <text x={cx + 12} y={ySat - 2} className="rm-lab">{s.occurred_at ? shortDate(s.occurred_at) : ""}</text>
                    <text x={cx + 12} y={ySat + 12} className="rm-ttl">{short(s.title, 18, 1)[0]}</text>
                    {station(s, cx, ySat, "rm-dotted")}
                  </g>
                );
              })}
            </g>
          )}
          {/* the main line's stations, labels beneath */}
          {trunk.map((s, i) => {
            const x = xs.get(s.id)!, here = s.id === currentId;
            const tag = i === 0 && s.id === shape.trunk[0]?.id ? "Root" : s.id === shape.trunk.at(-1)?.id ? "Latest" : here ? "You are here" : null;
            return (
              <g key={s.id}>
                {tag && <text x={x - 12} y={yMain + 4} textAnchor="end" className={`rm-k${here ? " rm-k-here" : ""}`}>{tag}</text>}
                <text x={x} y={yMain + 24} textAnchor="middle" className="rm-lab">{s.occurred_at ? shortDate(s.occurred_at) : ""}</text>
                <text x={x} y={yMain + 38} textAnchor="middle" className={`rm-ttl${here ? " rm-ttl-here" : ""}`}>
                  {short(s.title).map((ln, k) => <tspan key={k} x={x} dy={k ? 13 : 0}>{ln}</tspan>)}
                </text>
                {station(s, x, yMain, "")}
              </g>
            );
          })}
        </svg>
      </div>
      {hover && (
        <div className="rm-tip" style={{ left: Math.max(8, hover.x - 130), top: hover.y - yTop + 18 }} role="tooltip">
          <b>{hover.s.title}</b>
          <span className="font-mono text-[11px]" style={{ color: "var(--ink-muted)" }}>{facts(hover.s)}</span>
        </div>
      )}
      {picked && card(picked)}
    </div>
  );
}
