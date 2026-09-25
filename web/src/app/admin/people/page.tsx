"use client";

/**
 * Every account, newest first: who they are as they told us at onboarding, the
 * plan they are on, which days of the last four weeks they used Prism signed
 * in (a strip, one mark per day), and whether they label. Search and filter
 * the rows loaded here; read-only. The line under the title never states a
 * total above rows that are not all loaded (review, 2026-09-23): it says how
 * many of how many, and the next ones load on request.
 */

import { useEffect, useState } from "react";

import { AdminHead, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { dayLabel, days } from "@/components/admin/charts/format";
import { Act, Badge, FilterSwitch, SearchBox, matches } from "@/components/admin/ui";
import { Alert } from "@/components/ui";
import { adminCall, fetchPeople, type Person } from "@/lib/admin";
import { langName } from "@/lib/languages";

type People = Awaited<ReturnType<typeof fetchPeople>>;
type Plan = "all" | "plus" | "given" | "free";
// Live as the overview's "paying" counts it (common/metrics.money): active, or
// retrying a charge. A checkout left open or a plan that ended is free today;
// the line under the badge still says which plan it was.
const LIVE = new Set(["active", "past_due"]);
const PLAN_OF = (p: Person): Exclude<Plan, "all"> =>
  !p.plan || !LIVE.has(p.plan_status ?? "") ? "free" : p.provider === "manual" ? "given" : "plus";
const PLAN_WORD: Record<Plan, string> = { all: "All", plus: "Plus", given: "Given", free: "Free" };
const PLAN_TONE = { plus: "ink", given: "outline", free: "dashed" } as const;
/** An email as a row's name: mono, as typed (a table head's caps would change it). */
const EMAIL: React.CSSProperties = {
  font: "400 12px/1.4 var(--font-mono)",
  textTransform: "none",
  letterSpacing: 0,
  color: "var(--ink)",
  padding: 10,
  borderBottom: "1px solid var(--line)",
  verticalAlign: "top",
};
/** The API's page size (api/routes/admin_controls.people caps a read at 500). */
const PAGE = 500;

/** One mark per day of the window, filled on a day they used Prism signed in. */
function ActivityStrip({ on, start, length }: { on: string[]; start: string; length: number }) {
  const active = new Set(on);
  const last = on.at(-1);
  const label = on.length
    ? `Active on ${on.length} of the last ${length} days, last on ${dayLabel(last!)}`
    : `Not active in the last ${length} days`;
  return (
    <div role="img" aria-label={label} title={label} className="flex gap-[2px]">
      {days(start, length).map((d) => (
        <span key={d} className="h-3.5 w-[5px]" style={{ background: active.has(d) ? "var(--ink)" : "var(--line)" }} />
      ))}
    </div>
  );
}

export default function PeoplePage() {
  const { session } = useAdmin();
  const [data, setData] = useState<People | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [plan, setPlan] = useState<Plan>("all");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPeople(session)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load people"));
  }, [session]);

  const people = data?.people ?? [];
  const shown = people.filter((p) => (plan === "all" || PLAN_OF(p) === plan) && matches(query, p.email, p.name, p.profession, p.state));
  const all = !!data && people.length >= data.total;
  const line = !data
    ? null
    : [
        "NEWEST FIRST",
        all ? `${data.total.toLocaleString("en-IN")} ${data.total === 1 ? "ACCOUNT" : "ACCOUNTS"}` : `SHOWING THE NEWEST ${people.length.toLocaleString("en-IN")} OF ${data.total.toLocaleString("en-IN")}`,
        ...(shown.length < people.length ? [`${shown.length.toLocaleString("en-IN")} MATCH`] : []),
      ].join(" · ");

  const more = async () => {
    if (!data) return;
    setLoading(true);
    try {
      const next = await adminCall<People>(session, `/api/v1/admin/people?limit=${PAGE}&offset=${people.length}`);
      setData({ ...next, people: [...people, ...next.people] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load more people");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <AdminHead title="People" line={line} />
      {error && <Alert tone="error">{error}</Alert>}
      {people.length > 0 && (
        <div className="flex flex-wrap items-end gap-2.5">
          <SearchBox placeholder="Email, name, profession, state" value={query} onChange={setQuery} />
          <FilterSwitch
            label="Plan"
            value={plan}
            onChange={setPlan}
            options={(["all", "plus", "given", "free"] as const).map((v) => ({
              value: v,
              label: PLAN_WORD[v],
              count: v === "all" ? people.length : people.filter((p) => PLAN_OF(p) === v).length,
            }))}
          />
        </div>
      )}
      {data?.people.length === 0 && <Quiet>No accounts yet.</Quiet>}
      {people.length > 0 && shown.length === 0 && <Quiet>Nobody matches.</Quiet>}
      {data && shown.length > 0 && (
        <div className="admin-people min-w-0 overflow-x-auto">
          <table className="p-table">
            <thead>
              <tr>
                <th scope="col">Email</th>
                <th scope="col">What they told us</th>
                <th scope="col">Plan</th>
                <th scope="col">Last {data.active_window_days} days</th>
                <th scope="col" className="num">Days active · last</th>
                <th scope="col">Labeller</th>
                <th scope="col" className="num">Joined</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.email}>
                  <th scope="row" className="c-email max-lg:[overflow-wrap:anywhere] lg:whitespace-nowrap" style={EMAIL}>
                    {p.email}
                  </th>
                  <td className="c-told min-w-[180px]" style={{ color: "var(--ink-2)" }}>
                    {[p.name, p.profession, p.state, p.languages.map(langName).join(", ")].filter(Boolean).join(" · ") || "Nothing told us yet"}
                  </td>
                  <td className="c-plan">
                    <Badge tone={PLAN_TONE[PLAN_OF(p)]}>{PLAN_WORD[PLAN_OF(p)]}</Badge>
                    {p.plan && (
                      <span className="p-count mt-1 block">{`${p.plan.replace("_", " ")} · ${p.plan_status}${p.provider === "manual" ? " · given" : ""}`}</span>
                    )}
                  </td>
                  <td className="c-act">
                    <ActivityStrip on={p.active_on} start={data.window_start} length={data.active_window_days} />
                  </td>
                  <td className="c-meta num whitespace-nowrap text-[11.5px]" style={{ color: "var(--ink-3)" }}>
                    {p.active_days} {p.active_days === 1 ? "DAY" : "DAYS"}
                    {p.last_active && ` · LAST ${dayLabel(p.last_active).toUpperCase()}`}
                  </td>
                  <td className={`c-meta ${p.labeller ? "" : "max-lg:!hidden"}`} style={{ color: "var(--ink-2)" }}>
                    {p.labeller && <span className="lg:hidden">Labeller: </span>}
                    {p.labeller ? p.labeller[0].toUpperCase() + p.labeller.slice(1) : <span aria-label="Not a labeller">—</span>}
                  </td>
                  <td className="c-meta num whitespace-nowrap text-[11.5px]" style={{ color: "var(--ink-3)" }}>
                    <span className="lg:hidden">JOINED </span>
                    {dayLabel(p.created_at.slice(0, 10)).toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && !all && (
        <div className="flex flex-wrap items-center gap-3">
          <span className="p-count">
            NEWEST {people.length.toLocaleString("en-IN")} OF {data.total.toLocaleString("en-IN")}
          </span>
          <Act variant="secondary" disabled={loading} onClick={() => void more()}>
            {loading ? "Loading…" : `Load the next ${Math.min(PAGE, data.total - people.length).toLocaleString("en-IN")}`}
          </Act>
        </div>
      )}
    </>
  );
}
