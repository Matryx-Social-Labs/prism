"use client";

/**
 * Marketing: make a link to any public Prism page for one platform, with its
 * UTM tags and a short address (common/share_links.py), a post written from
 * the page's facts and its share images; then see what each link brought.
 *
 * What the numbers are, as the attribution skill has it: directional, never
 * "caused". A visit is the first page of a visit whose link carried the code
 * (JavaScript on, not a bot), so a platform's own click count is higher; what
 * it did next is counted in the same tab; nothing is known about who. Links
 * shared in chats lose their referrer, so what readers say brought them
 * (asked once, from a list) sits beside the counts, and the platform word
 * of every tagged link, hand-made ones included.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { AdminHead, AdminSection, useAdmin } from "@/components/admin/AdminShell";
import { BarList } from "@/components/admin/charts/Bars";
import { ChartPanel } from "@/components/admin/charts/ChartPanel";
import { dayLabel } from "@/components/admin/charts/format";
import { LinkBuilder } from "@/components/admin/marketing/LinkBuilder";
import { LinkResult } from "@/components/admin/marketing/LinkResult";
import { LinksTable, platformName } from "@/components/admin/marketing/LinksTable";
import { Alert } from "@/components/ui";
import { type Breakdown, type CountedLink, type LinksPayload, type ShareLink, fetchLinks, fetchMetrics, setLinkArchived } from "@/lib/admin";
import { type Facts, PLATFORM_LABEL, type Platform } from "@/lib/shareLinks";

const PERIODS = [7, 28, 90] as const;
const SOURCE = "usage_daily · founder links · visits and what they did next, never who";

/** Visits and accounts added up under a label (platform or campaign), most visits first. */
function rollup(links: CountedLink[], key: (l: CountedLink) => string) {
  const by = new Map<string, { visits: number; accounts: number }>();
  for (const l of links) {
    const k = key(l);
    const t = by.get(k) ?? { visits: 0, accounts: 0 };
    by.set(k, { visits: t.visits + l.visits, accounts: t.accounts + (l.goals.account ?? 0) });
  }
  return [...by].map(([label, t]) => ({ label, ...t })).sort((a, b) => b.visits - a.visits);
}

function Rollup({ title, rows }: { title: string; rows: ReturnType<typeof rollup> }) {
  const drawn = rows.filter((r) => r.visits > 0);
  return (
    <ChartPanel title={title} source={SOURCE} empty={drawn.length ? null : "No visits by a founder link in this period."}
      table={{ columns: ["", "Visits", "Accounts"], rows: rows.map((r) => [r.label, r.visits, r.accounts]) }}>
      <BarList rows={drawn.map((r) => ({ label: r.label, current: r.visits }))} />
    </ChartPanel>
  );
}

function FromMetrics({ b }: { b: Breakdown | undefined }) {
  if (!b) return null;
  const rows = b.rows.filter((r) => r.current !== null && r.current > 0);
  return (
    <ChartPanel title={b.title} source={b.source} empty={rows.length ? null : "Nothing in this period."}
      table={{ columns: ["", "This period"], rows: b.rows.map((r) => [r.label, r.current]) }}>
      <BarList rows={rows} names={b.key === "campaigns" ? PLATFORM_LABEL : undefined} />
    </ChartPanel>
  );
}

export default function MarketingPage() {
  const { session } = useAdmin();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(28);
  const [data, setData] = useState<LinksPayload | null>(null);
  const [said, setSaid] = useState<{ heard?: Breakdown; campaigns?: Breakdown }>({});
  const [made, setMade] = useState<{ link: ShareLink; facts: Facts; platform: Platform } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  // The period last asked for: a slow 90-day answer must not land over the 7 days asked for after it.
  const asked = useRef(days);
  asked.current = days;
  const load = useCallback(async () => {
    try {
      const links = await fetchLinks(session, days);
      if (asked.current !== days) return;
      setData(links);
      setError("");
    } catch (e) {
      if (asked.current === days) setError(e instanceof Error ? e.message : "Could not load the links");
    }
  }, [session, days]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    // What readers say brought them, and every tagged link by platform: the Overview's own counts.
    let live = true;
    fetchMetrics(session, days)
      .then((m) => {
        const visits = m.sections.find((s) => s.key === "visits")?.breakdowns ?? [];
        if (live) setSaid({ heard: visits.find((b) => b.key === "heard"), campaigns: visits.find((b) => b.key === "campaigns") });
      })
      .catch(() => live && setSaid({}));
    return () => {
      live = false;
    };
  }, [session, days]);

  const archive = async (code: string, archived: boolean) => {
    setBusy(code);
    setError("");
    try {
      await setLinkArchived(session, code, archived);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not save");
    } finally {
      setBusy(null);
    }
  };

  const range = data ? `${dayLabel(data.range.start)} – ${dayLabel(data.range.end)} IST · visits and what they did next, never who`.toUpperCase() : null;
  return (
    <>
      <AdminHead title="Marketing" line={range}>
        <div className="p-seg" role="tablist" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} type="button" role="tab" aria-selected={days === p} onClick={() => setDays(p)}>
              {p} days
            </button>
          ))}
        </div>
      </AdminHead>
      {error && <Alert tone="error">{error}</Alert>}

      {data && (
        <AdminSection title="Make a link" hint="A link to one Prism page for one platform: its tags, a short address, a post and the page's share images.">
          <LinkBuilder data={data} onMade={(link, facts, platform) => {
            setMade({ link, facts, platform });
            void load();
          }} />
          {made && <LinkResult key={made.link.code} link={made.link} facts={made.facts} platform={made.platform} />}
        </AdminSection>
      )}

      {data && (
        <AdminSection title="What the links brought" sub={`${data.links.length} ${data.links.length === 1 ? "LINK" : "LINKS"}`}
          hint="Directional, not proof: a visit came by the link; what it did next happened in the same tab.">
          <div className="grid grid-cols-[minmax(0,1fr)] gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Rollup title="Founder links, by platform" rows={rollup(data.links, (l) => platformName(l.platform))} />
            <Rollup title="Founder links, by campaign" rows={rollup(data.links, (l) => l.campaign || "no campaign")} />
            <FromMetrics b={said.campaigns} />
            <FromMetrics b={said.heard} />
          </div>
        </AdminSection>
      )}

      {data && (
        <AdminSection title="Links" hint="Open a link for its visits day by day. Archive hides it here; a posted link keeps working.">
          <LinksTable data={data} onArchive={(code, archived) => void archive(code, archived)} busy={busy} />
        </AdminSection>
      )}
    </>
  );
}
