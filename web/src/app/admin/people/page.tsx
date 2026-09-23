"use client";

/**
 * Every account, newest first: who they are as they told us at onboarding, the
 * plan they are on, how many days of the last four weeks they used Prism
 * signed in, and whether they label. Read-only.
 */

import { useEffect, useState } from "react";

import { AdminSection, AdminTitle, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { dayLabel } from "@/components/admin/Ledger";
import { fetchPeople, type Person } from "@/lib/admin";
import { langName } from "@/lib/languages";

export default function PeoplePage() {
  const { session } = useAdmin();
  const [data, setData] = useState<{ total: number; active_window_days: number; people: Person[] } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPeople(session)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load people"));
  }, [session]);

  return (
    <>
      <AdminTitle>People</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      {/* Never a total above rows that are not all there (review, 2026-09-23). */}
      <AdminSection
        title={!data ? "Accounts" : data.people.length < data.total ? `Accounts · newest ${data.people.length} of ${data.total}` : `Accounts · ${data.total}`}
      >
        {data?.people.length === 0 && <Quiet>No accounts yet.</Quiet>}
        {data && data.people.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-[14px]">
              <thead>
                <tr className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
                  <th scope="col" className="py-2 pr-4 font-semibold">Account</th>
                  <th scope="col" className="py-2 pr-4 font-semibold">Plan</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">Days active, last {data.active_window_days}</th>
                  <th scope="col" className="py-2 pr-4 font-semibold">Labels</th>
                  <th scope="col" className="py-2 font-semibold">Joined</th>
                </tr>
              </thead>
              <tbody>
                {data.people.map((p) => (
                  <tr key={p.email} className="border-t align-top" style={{ borderColor: "var(--line)" }}>
                    <th scope="row" className="py-2.5 pr-4 font-normal">
                      <span className="block" style={{ color: "var(--ink)" }}>{p.email}</span>
                      <span className="block text-[13px]" style={{ color: "var(--ink-2)" }}>
                        {[p.name, p.profession, p.state, p.languages.map(langName).join(", ")].filter(Boolean).join(" · ") || "Nothing told us yet"}
                      </span>
                    </th>
                    <td className="py-2.5 pr-4" style={{ color: "var(--ink-2)" }}>
                      {p.plan ? `${p.plan.replace("_", " ")} · ${p.plan_status}${p.provider === "manual" ? " · given" : ""}` : "Free"}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono tabular-nums">
                      {p.active_days}
                      {p.last_active && (
                        <span className="block text-[11px]" style={{ color: "var(--ink-3)" }}>LAST {dayLabel(p.last_active).toUpperCase()}</span>
                      )}
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
