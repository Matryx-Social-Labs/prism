"use client";

/**
 * Review a practice round or a test before labellers see it: every item with
 * its answer and the explanation a labeller reads when they miss it. The
 * explanations are machine drafts until a founder has read them. Publish is
 * refused (by the API, common/label_ops.set_open) while any item is
 * unexplained or a constant strategy — always yes, always no — would pass.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminSection, AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { fetchRound, saveExplanations, setOpen, type RoundCheck, type RoundItem } from "@/lib/admin";

export default function RoundReview({ params }: { params: Promise<{ key: string }> }) {
  const { session } = useAdmin();
  const [key, setKey] = useState("");
  const [items, setItems] = useState<RoundItem[] | null>(null);
  const [check, setCheck] = useState<RoundCheck | null>(null);
  const [edits, setEdits] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    params.then((p) => setKey(p.key));
  }, [params]);

  const load = useCallback(async () => {
    if (!key) return;
    try {
      const r = await fetchRound(session, key);
      setItems(r.items);
      setCheck(r.check);
      setEdits({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this round");
    }
  }, [session, key]);

  useEffect(() => {
    void load();
  }, [load]);

  const changed = Object.entries(edits).map(([position, explanation]) => ({ position: Number(position), explanation }));

  const save = async () => {
    setError("");
    try {
      const r = await saveExplanations(session, key, changed);
      setNote(`${r.saved} saved`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    }
  };

  const publish = async () => {
    setError("");
    try {
      await setOpen(session, key, true);
      setNote("Published: labellers can take it now");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Publishing was refused");
    }
  };

  return (
    <>
      <p className="mt-6 text-[14px]">
        <Link href="/admin/batches" className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>
          All batches
        </Link>
      </p>
      <AdminTitle>{check?.name ?? "Round"}</AdminTitle>
      {error && (
        <p role="alert" className="mt-5 text-[14px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      {note && (
        <p aria-live="polite" className="mt-5 text-[14px]" style={{ color: "var(--ink-2)" }}>
          {note}
        </p>
      )}
      {check && (
        <AdminSection title={check.ok ? "Ready to publish" : "Not publishable yet"}>
          {check.reasons.length > 0 && (
            <ul className="list-disc pl-5 text-[15px]">
              {check.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
            {check.items} ITEMS · {check.missing} WITHOUT AN EXPLANATION ·{" "}
            {Object.entries(check.scores)
              .map(([s, v]) => `${s.toUpperCase()} ${Math.round(v * 100)}%`)
              .join(" · ")}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" className="btn btn-primary" disabled={changed.length === 0} onClick={() => void save()}>
              Save {changed.length > 0 ? changed.length : ""} {changed.length === 1 ? "change" : "changes"}
            </button>
            <button type="button" className="btn btn-secondary" disabled={!check.ok || changed.length > 0} onClick={() => void publish()}>
              Publish
            </button>
          </div>
        </AdminSection>
      )}
      <AdminSection title="Items">
        <ol>
          {items?.map((it) => (
            <li key={it.position} className="border-t py-4" style={{ borderColor: "var(--line)" }}>
              <p className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                #{it.position + 1} · ANSWER {it.answer.toUpperCase()}
              </p>
              {it.speaker && <p className="mt-1 text-[15px] font-semibold">{it.speaker}</p>}
              {it.quote && (
                <p className="mt-1 text-[15px] italic leading-[1.55]" style={{ fontFamily: "var(--font-display), serif" }}>
                  “{it.quote}”
                </p>
              )}
              <label className="mt-2 block">
                <span className="sr-only">Explanation for item {it.position + 1}</span>
                <textarea
                  className="w-full rounded-[8px] border p-3 text-[15px] leading-[1.55]"
                  style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}
                  rows={3}
                  maxLength={2000}
                  value={edits[it.position] ?? it.explanation}
                  onChange={(e) => setEdits((x) => ({ ...x, [it.position]: e.target.value }))}
                />
              </label>
            </li>
          ))}
        </ol>
      </AdminSection>
    </>
  );
}
