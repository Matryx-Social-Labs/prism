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

import { AdminHead, AdminSection, useAdmin } from "@/components/admin/AdminShell";
import { CountedIn, DataTable, InfoButton } from "@/components/admin/charts/ChartPanel";
import { dayLabel, share } from "@/components/admin/charts/format";
import { langWord, languageColours } from "@/components/admin/coverage/colours";
import { NetStage, NetworkFrame, hasWebGL, type NetState } from "@/components/admin/coverage/NetworkFrame";
import { Alert, EmptyState } from "@/components/ui";
import { fetchCoverage, type Coverage } from "@/lib/admin";

const CoverageGraph = dynamic(() => import("@/components/admin/coverage/CoverageGraph"), {
  ssr: false,
  loading: () => (
    <NetStage>
      <span className="text-[14px]" style={{ color: "var(--ink-2)" }}>
        Loading the network…
      </span>
    </NetStage>
  ),
});

const PERIODS = [7, 28, 90] as const;
const LISTED = 30;
const LINKS = 15;

/** A section whose numbers keep their source behind the ⓘ. */
function Sourced({ title, sub, source, note, children }: { title: string; sub?: string; source: string; note: string; children: React.ReactNode }) {
  const [info, setInfo] = useState(false);
  return (
    <AdminSection title={title} sub={sub} right={<InfoButton label={title} open={info} onToggle={() => setInfo((v) => !v)} />}>
      {info && <CountedIn source={source} note={note} />}
      <div className="min-w-0">{children}</div>
    </AdminSection>
  );
}

export default function CoveragePage() {
  const { session } = useAdmin();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(28);
  const [data, setData] = useState<Coverage | null>(null);
  const [error, setError] = useState("");
  const [net, setNet] = useState<NetState>("closed");

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
  // The 3D view is the network: an outlet that shared no story has no place in
  // it and would only crowd the frame. The tables still list it.
  const linked = new Set(data?.links.flatMap((l) => [l.a, l.b]) ?? []);
  const inNetwork = data?.outlets.filter((o) => linked.has(o.id)) ?? [];
  const alone = (data?.outlets.length ?? 0) - inNetwork.length;
  // No story has two outlets: each story is one outlet's, so the languages'
  // totals add up to the stories.
  const unshared = !!data && data.outlets.length > 0 && data.outlets.every((o) => o.shared === 0);
  const stories = data?.per_language.reduce((n, l) => n + l.stories, 0) ?? 0;
  const count = (n: number) => n.toLocaleString("en-IN");

  const open = () => setNet(hasWebGL() ? "open" : "nowebgl");

  return (
    <>
      <AdminHead
        title="Coverage"
        line={data && `Which outlets reported the same stories · ${dayLabel(data.range.start)} – ${dayLabel(data.range.end)} IST`.toUpperCase()}
      >
        <div className="p-seg" role="tablist" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} type="button" role="tab" aria-selected={days === p} onClick={() => setDays(p)}>
              {p} days
            </button>
          ))}
        </div>
      </AdminHead>
      {error && <Alert tone="error">{error}</Alert>}

      {data && data.outlets.length === 0 && (
        <EmptyState title="No stories in this period">Coverage links appear once two outlets report the same story.</EmptyState>
      )}
      {unshared && (
        <EmptyState title="No story has two outlets yet">
          Coverage links appear once two outlets report the same story. In this period: {count(stories)} {stories === 1 ? "story" : "stories"}, each from
          one outlet so far.
        </EmptyState>
      )}

      {data && data.outlets.length > 0 && !unshared && (
        <div className="grid gap-5 lg:grid-cols-2 lg:gap-6">
          <Sourced
            title="Stories in two languages"
            sub="PAIR · IN BOTH · EACH LANGUAGE'S TOTAL"
            source={data.source}
            note="A story counts once for a pair of languages, however many outlets in each carried it. Beside each pair, how many stories each language reported in all."
          >
            {data.languages.length ? (
              <DataTable
                table={{
                  columns: ["Pair", "In both", "First total", "Second total"],
                  rows: data.languages.map((p) => [`${langWord(p.a)} · ${langWord(p.b)}`, p.stories, perLang.get(p.a) ?? null, perLang.get(p.b) ?? null]),
                }}
              />
            ) : (
              <p className="py-2 text-[14px]" style={{ color: "var(--ink-2)" }}>
                No story was reported in more than one language.
              </p>
            )}
          </Sourced>
          <Sourced
            title="Strongest links"
            sub={data.links.length > LINKS ? `TOP ${LINKS} OF ${count(data.links.length)} OUTLET PAIRS` : "OUTLET PAIRS · STORIES BOTH REPORTED"}
            source={data.source}
            note="The pairs of outlets that reported the most stories in common."
          >
            <DataTable
              table={{
                columns: ["Outlets", "Both reported"],
                rows: data.links.slice(0, LINKS).map((l) => [`${byId.get(l.a)?.name ?? "?"} · ${byId.get(l.b)?.name ?? "?"}`, l.shared]),
              }}
            />
          </Sourced>
        </div>
      )}

      {data && data.outlets.length > 0 && (
        <Sourced
          title="Outlets"
          sub={
            data.outlets.length > LISTED
              ? `${LISTED} OF ${count(data.outlets.length)} OUTLETS · MOST STORIES FIRST`
              : `${count(data.outlets.length)} ${data.outlets.length === 1 ? "OUTLET" : "OUTLETS"} WITH A STORY`
          }
          source={data.source}
          note="Stories an outlet reported in the period, and how many of them at least one other outlet also reported."
        >
          <DataTable
            table={{
              columns: ["Outlet", "Language", "Stories", "Also reported elsewhere"],
              text: [1],
              rows: data.outlets.slice(0, LISTED).map((o) => [o.name, langWord(o.language), o.stories, share(o.shared, o.stories)]),
            }}
          />
        </Sourced>
      )}

      {data && data.outlets.length > 0 && !unshared && (
        <NetworkFrame
          state={net}
          onOpen={open}
          left={alone}
          legend={key.map((k) => ({ ...k, total: count(inNetwork.filter((o) => colour(o.language) === k.color).length) }))}
        >
          <CoverageGraph
            outlets={inNetwork.map((o) => ({ id: o.id, name: o.name, language: o.language, stories: o.stories, color: colour(o.language) }))}
            links={data.links}
            label={`${inNetwork.length} outlets and ${data.links.length} links between them; the tables on this page list the same numbers.`}
          />
        </NetworkFrame>
      )}
    </>
  );
}
