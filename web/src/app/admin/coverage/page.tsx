"use client";

/**
 * Who covers what with whom (common/coverage.py; founder decision V4,
 * 2026-09-24). Outlets are linked by the stories both reported. The tables
 * come first and carry every number; the 3D network is drawn from the same
 * data, and its code loads only when a founder opens it.
 *
 * What to look for: a language whose outlets link mostly among themselves is
 * an island. Few stories reported in two languages while each language
 * reports plenty is what the cross-language merge hole looks like from here —
 * a count, not a verdict on any one story.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { ChartPanel, DataTable, SeriesKey } from "@/components/admin/charts/ChartPanel";
import { dayLabel, share } from "@/components/admin/charts/format";
import { langWord, languageColours } from "@/components/admin/coverage/colours";
import { fetchCoverage, type Coverage } from "@/lib/admin";

const CoverageGraph = dynamic(() => import("@/components/admin/coverage/CoverageGraph"), {
  ssr: false,
  loading: () => <p className="py-10 text-center text-[14px]" style={{ color: "var(--ink-2)" }}>Loading the 3D view…</p>,
});

const PERIODS = [7, 28, 90] as const;
const LISTED = 30;

export default function CoveragePage() {
  const { session } = useAdmin();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(28);
  const [data, setData] = useState<Coverage | null>(null);
  const [error, setError] = useState("");
  const [open3d, setOpen3d] = useState(false);

  useEffect(() => {
    // A slow 90-day answer must not land over the 7 days asked for after it.
    let current = true;
    setError("");
    fetchCoverage(session, days)
      .then((d) => current && setData(d))
      .catch((e: unknown) => current && setError(e instanceof Error ? e.message : "Could not load coverage"));
    return () => {
      current = false;
    };
  }, [session, days]);

  const byId = new Map(data?.outlets.map((o) => [o.id, o]) ?? []);
  const perLang = new Map(data?.per_language.map((l) => [l.language, l.stories]) ?? []);
  const { colour, key } = languageColours(data?.per_language ?? []);
  const empty = data && data.outlets.length === 0 ? "No stories were formed in this period." : null;
  // The 3D view is the network: an outlet that shared no story has no place in
  // it and would only crowd the frame. The tables still list it.
  const linked = new Set(data?.links.flatMap((l) => [l.a, l.b]) ?? []);
  const inNetwork = data?.outlets.filter((o) => linked.has(o.id)) ?? [];
  const alone = (data?.outlets.length ?? 0) - inNetwork.length;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <AdminTitle>Coverage</AdminTitle>
          {data && (
            <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
              {dayLabel(data.range.start).toUpperCase()} – {dayLabel(data.range.end).toUpperCase()} · IST · {data.outlets.length} OUTLETS ·{" "}
              {data.links.length} LINKS
            </p>
          )}
        </div>
        <div className="seg" role="tablist" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} type="button" role="tab" aria-selected={days === p} onClick={() => setDays(p)}>
              {p} days
            </button>
          ))}
        </div>
      </div>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      {data && (
        <div className="mt-8 grid gap-4 lg:grid-cols-2">
          <ChartPanel
            title="Stories reported in two languages"
            source={data.source}
            note="A story counts once for a pair of languages, however many outlets in each carried it. Beside each pair, how many stories each language reported in all."
            empty={empty ?? (data.languages.length ? null : "No story was reported in more than one language.")}
          >
            <DataTable
              table={{
                columns: ["Languages", "In both", "Each, in all"],
                rows: data.languages.map((p) => [
                  `${langWord(p.a)} + ${langWord(p.b)}`,
                  p.stories,
                  `${(perLang.get(p.a) ?? 0).toLocaleString("en-IN")} · ${(perLang.get(p.b) ?? 0).toLocaleString("en-IN")}`,
                ]),
              }}
            />
          </ChartPanel>

          <ChartPanel
            title="Strongest links"
            source={data.source}
            note="The pairs of outlets that reported the most stories in common."
            empty={empty ?? (data.links.length ? null : "No two outlets reported the same story.")}
          >
            <DataTable
              table={{
                columns: ["Outlets", "Stories both reported"],
                rows: data.links.slice(0, 15).map((l) => [`${byId.get(l.a)?.name ?? "?"} + ${byId.get(l.b)?.name ?? "?"}`, l.shared]),
              }}
            />
          </ChartPanel>

          <ChartPanel
            title="The network in 3D"
            source={data.source}
            className="lg:col-span-2"
            note="Each sphere is an outlet, sized by the stories it reported and coloured by its language. A line joins two outlets that reported the same story, darker the more they share. Drag to turn, scroll to zoom."
            empty={empty}
          >
            {open3d ? (
              <CoverageGraph
                outlets={inNetwork.map((o) => ({ id: o.id, name: o.name, language: o.language, stories: o.stories, color: colour(o.language) }))}
                links={data.links}
                label={`${inNetwork.length} outlets and ${data.links.length} links between them; the tables on this page list the same numbers.`}
              />
            ) : (
              <div className="flex min-h-[160px] flex-col items-center justify-center gap-3 rounded-[var(--r-md)]" style={{ background: "var(--sunken)" }}>
                <p className="max-w-[46ch] px-4 text-center text-[14px]" style={{ color: "var(--ink-2)" }}>
                  {inNetwork.length} outlets, {data.links.length} links. The 3D view loads when you open it.
                </p>
                <button type="button" className="btn btn-secondary" onClick={() => setOpen3d(true)}>
                  Open the 3D view
                </button>
              </div>
            )}
            <SeriesKey items={key} />
            {alone > 0 && (
              <p className="mt-2 text-[12.5px]" style={{ color: "var(--ink-2)" }}>
                {alone} {alone === 1 ? "outlet" : "outlets"} that shared no story with another {alone === 1 ? "is" : "are"} left out of the 3D view; the table below lists {alone === 1 ? "it" : "them"}.
              </p>
            )}
          </ChartPanel>

          <ChartPanel
            title={data.outlets.length > LISTED ? `Outlets · ${LISTED} of ${data.outlets.length}` : "Outlets"}
            source={data.source}
            className="lg:col-span-2"
            note="Stories an outlet reported in the period, and how many of them at least one other outlet also reported."
            empty={empty}
          >
            <DataTable
              table={{
                columns: ["Outlet", "Language", "Stories", "Also reported elsewhere"],
                rows: data.outlets.slice(0, LISTED).map((o) => [o.name, langWord(o.language), o.stories, share(o.shared, o.stories)]),
              }}
            />
          </ChartPanel>
        </div>
      )}
    </>
  );
}
