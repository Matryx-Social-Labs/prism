"use client";

/**
 * What the models cost (common/spend.py, 2026-09-27). Every chat call, Jev
 * decision, Ask answer and podcast transcription adds OpenRouter's own cost to
 * a ledger per stage per UTC day; this page reads it back.
 *
 * What to look for: extraction was ~78% of the bill when the ledger was built.
 * Its cached share should sit near 80% since the schema moved ahead of the
 * article — if it falls, the prefix changed and every call is paying full
 * price again. Days before the ledger existed read "not recorded", not $0.
 */

import { useEffect, useState } from "react";

import { AdminHead, AdminSection, useAdmin } from "@/components/admin/AdminShell";
import { CountedIn, DataTable, InfoButton } from "@/components/admin/charts/ChartPanel";
import { Alert, EmptyState } from "@/components/ui";
import { byStage, fetchSpend, runwayDays, usd, type Spend } from "@/lib/admin";

const PERIODS = [7, 14, 30] as const;
const SOURCE = "common/spend.py · OpenRouter usage.cost on every model call";
const tokens = (n: number) => n.toLocaleString("en-IN");

function Sourced({ title, sub, note, children }: { title: string; sub?: string; note: string; children: React.ReactNode }) {
  const [info, setInfo] = useState(false);
  return (
    <AdminSection title={title} sub={sub} right={<InfoButton label={title} open={info} onToggle={() => setInfo((v) => !v)} />}>
      {info && <CountedIn source={SOURCE} note={note} />}
      <div className="min-w-0">{children}</div>
    </AdminSection>
  );
}

export default function SpendPage() {
  const { session } = useAdmin();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(14);
  const [data, setData] = useState<Spend | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let current = true;
    setError("");
    fetchSpend(session, days)
      .then((d) => current && setData(d))
      .catch((e: unknown) => current && setError(e instanceof Error ? e.message : "Could not load spend"));
    return () => {
      current = false;
    };
  }, [session, days]);

  const recorded = data?.days.filter((d) => d.recorded) ?? [];
  const total = recorded.reduce((n, d) => n + d.cost, 0);
  const stages = data ? byStage(data) : [];
  const runway = data ? runwayDays(data) : null;

  return (
    <>
      <AdminHead title="Spend" line={"What the models cost · per stage · per UTC day".toUpperCase()}>
        <div className="p-seg" role="tablist" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} type="button" role="tab" aria-selected={days === p} onClick={() => setDays(p)}>
              {p} days
            </button>
          ))}
        </div>
      </AdminHead>
      {error && <Alert tone="error">{error}</Alert>}

      {data && recorded.length === 0 && (
        <EmptyState title="Nothing recorded yet">
          The ledger starts with the first model call after it shipped. Earlier days are not counted here.
        </EmptyState>
      )}

      {data && (
        <Sourced
          title="Balance"
          sub="OPENROUTER · THE FLOOR STOPS COLLECTION"
          note="The balance is read from OpenRouter every fifteen minutes (common/budget.py). Runway divides what is left above the floor by the recorded days' average."
        >
          <DataTable
            table={{
              columns: ["", "Value"],
              rows: [
                ["Balance", data.balance ? usd(data.balance.balance) : "not read yet"],
                ["Floor", usd(data.floor)],
                [`Spent, ${recorded.length} recorded ${recorded.length === 1 ? "day" : "days"}`, usd(total)],
                ["Average per recorded day", recorded.length ? usd(total / recorded.length) : "—"],
                ["Runway to the floor", runway === null ? "—" : `${runway.toFixed(1)} days`],
              ],
            }}
          />
        </Sourced>
      )}

      {data && recorded.length > 0 && (
        <div className="grid gap-5 lg:grid-cols-2 lg:gap-6">
          <Sourced title="By day" sub="UTC DAY · CALLS · COST" note="Every model call recorded that day. A day before the ledger existed reads 'not recorded'.">
            <DataTable
              table={{
                columns: ["Day", "Calls", "Cost"],
                rows: data.days.map((d) => [d.day, d.recorded ? d.calls : null, d.recorded ? usd(d.cost) : "not recorded"]),
              }}
            />
          </Sourced>
          <Sourced
            title="By stage"
            sub={`${stages.length} STAGES · MOST EXPENSIVE FIRST`}
            note="Stage is the trace name the call was made under. Cached is the share of input tokens the provider served from its prompt cache, billed at a tenth."
          >
            <DataTable
              table={{
                columns: ["Stage", "Model", "Calls", "Cost", "Share", "Cached", "Output tokens"],
                text: [1],
                rows: stages.map((s) => [
                  s.stage,
                  s.model,
                  s.calls,
                  usd(s.cost),
                  total > 0 ? `${Math.round((s.cost / total) * 100)}%` : "—",
                  s.input_tokens ? `${Math.round((s.cached_tokens / s.input_tokens) * 100)}%` : "—",
                  tokens(s.output_tokens),
                ]),
              }}
            />
          </Sourced>
        </div>
      )}
    </>
  );
}
