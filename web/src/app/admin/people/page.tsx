"use client";

/**
 * Every account, newest first: who they are as they told us at onboarding, the
 * plan they are on, which days of the last four weeks they used Prism signed
 * in (a strip, one mark per day), and whether they label. Search and filter
 * the rows loaded here; read-only.
 */

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { dayLabel, days } from "@/components/admin/charts/format";
import { Badge, FilterSeg, SearchBox, matches } from "@/components/admin/ui";
import { fetchPeople, type Person } from "@/lib/admin";
import { langName } from "@/lib/languages";

type Plan = "all" | "plus" | "given" | "free";
// Live as the overview's "paying" counts it (common/metrics.money): active, or
// retrying a charge. A checkout left open or a plan that ended is free today;
// the line under the badge still says which plan it was.
const LIVE = new Set(["active", "past_due"]);
const PLAN_OF = (p: Person): Exclude<Plan, "all"> =>
  !p.plan || !LIVE.has(p.plan_status ?? "") ? "free" : p.provider === "manual" ? "given" : "plus";
const PLAN_WORD: Record<Plan, string> = { all: "All", plus: "Plus", given: "Given", free: "Free" };

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
        <span
          key={d}
          className="h-3 w-[5px] rounded-[1px]"
          style={{ background: active.has(d) ? "var(--viz-1)" : "var(--sunken)" }}
        />
      ))}
    </div>
  );
}

export default function PeoplePage() {
  const { session } = useAdmin();
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchPeople>> | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [plan, setPlan] = useState<Plan>("all");

  useEffect(() => {
    fetchPeople(session)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load people"));
  }, [session]);

  const people = data?.people ?? [];
  const shown = people.filter(
    (p) => (plan === "all" || PLAN_OF(p) === plan) && matches(query, p.email, p.name, p.profession, p.state),
  );
  const loaded = !data ? "Accounts" : people.length < data.total ? `newest ${people.length} of ${data.total}` : `${data.total}`;

  return (
    <>
      <AdminTitle>People</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      {/* Never a total above rows that are not all there (review, 2026-09-23). */}
      <AdminSection title={!data ? "Accounts" : shown.length < people.length ? `Accounts · ${shown.length} of ${loaded}` : `Accounts · ${loaded}`}>
        {people.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <SearchBox label="Search by email, name, profession or state" value={query} onChange={setQuery} />
            <FilterSeg
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
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-[14px]">
              <thead>
                <tr className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
                  <th scope="col" className="py-2 pr-4 font-semibold">Account</th>
                  <th scope="col" className="py-2 pr-4 font-semibold">Plan</th>
                  <th scope="col" className="py-2 pr-4 font-semibold">Last {data.active_window_days} days</th>
                  <th scope="col" className="py-2 pr-4 font-semibold">Labels</th>
                  <th scope="col" className="py-2 font-semibold">Joined</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((p) => (
                  <tr key={p.email} className="border-t align-top" style={{ borderColor: "var(--line)" }}>
                    <th scope="row" className="py-2.5 pr-4 font-normal">
                      <span className="block" style={{ color: "var(--ink)" }}>{p.email}</span>
                      <span className="block text-[13px]" style={{ color: "var(--ink-2)" }}>
                        {[p.name, p.profession, p.state, p.languages.map(langName).join(", ")].filter(Boolean).join(" · ") || "Nothing told us yet"}
                      </span>
                    </th>
                    <td className="py-2.5 pr-4">
                      <Badge strong={PLAN_OF(p) === "plus"}>{PLAN_WORD[PLAN_OF(p)]}</Badge>
                      {p.plan && (
                        <span className="mt-1 block text-[12.5px]" style={{ color: "var(--ink-2)" }}>
                          {`${p.plan.replace("_", " ")} · ${p.plan_status}${p.provider === "manual" ? " · given" : ""}`}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-4">
                      <ActivityStrip on={p.active_on} start={data.window_start} length={data.active_window_days} />
                      <span className="mt-1 block font-mono text-[11px] tabular-nums" style={{ color: "var(--ink-3)" }}>
                        {p.active_days} {p.active_days === 1 ? "DAY" : "DAYS"}
                        {p.last_active && ` · LAST ${dayLabel(p.last_active).toUpperCase()}`}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4" style={{ color: "var(--ink-2)" }}>{p.labeller ?? "—"}</td>
                    <td className="py-2.5 font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{dayLabel(p.created_at.slice(0, 10))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminSection>
    </>
  );
}
