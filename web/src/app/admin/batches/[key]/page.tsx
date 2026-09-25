"use client";

/**
 * Review a practice round or a test before labellers see it: every item with
 * its answer and the explanation a labeller reads when they miss it. The
 * explanations are machine drafts until a founder has read them. Publish is
 * refused (by the API, common/label_ops.set_open) while the quality check
 * fails — an item unexplained, a constant strategy (always yes, always no)
 * that would pass, a test too short — so the button waits on the same check,
 * shown beside the items as verdicts.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminTitle, useAdmin } from "@/components/admin/AdminShell";
import { ArrowLeft } from "@/components/icons";
import { Verdict } from "@/components/label/parts";
import { Alert, TextField } from "@/components/ui";
import { fetchRound, saveExplanations, setOpen, type RoundCheck, type RoundItem } from "@/lib/admin";

const PURPOSE_WORD: Record<string, string> = { qualify: "TEST", practice: "PRACTICE ROUND", work: "WORK" };
const STRATEGY_WORD: Record<string, string> = { "tick nothing / always no": "Always no", "tick everything / always yes": "Always yes" };
// The API's reasons (common/label_ops.check_round) that the two checks below
// already say in their own words; any other reason is printed as it came.
const SAID = [/have no explanation/, /would pass it without reading/];

const two = (n: number) => String(n).padStart(2, "0");

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

  // As saved: the check is the server's, over what it holds.
  const unexplained = items?.filter((it) => !it.explanation.trim()) ?? [];
  const blocked = check && !check.ok ? (check.missing ? `fix ${check.missing} ${check.missing === 1 ? "item" : "items"} first` : "the check must pass") : null;
  const publishLabel = changed.length > 0 ? "Publish · save first" : blocked ? `Publish · ${blocked}` : "Publish";

  return (
    <>
      <Link href="/admin/batches" className="inline-flex min-h-[44px] items-center gap-1.5 self-start justify-self-start text-[14px] font-semibold" style={{ color: "var(--accent)" }}>
        <ArrowLeft size={16} />
        Batches
      </Link>
      <div className="flex flex-wrap items-end gap-2.5">
        <div className="min-w-0 flex-[1_1_300px]">
          {check && (
            <p className="p-count">
              {key.toUpperCase()} · {PURPOSE_WORD[check.purpose] ?? check.purpose.toUpperCase()} · {check.items} {check.items === 1 ? "ITEM" : "ITEMS"}
            </p>
          )}
          <AdminTitle>{check ? `Review: ${check.name}` : "Review"}</AdminTitle>
        </div>
        {check && (
          <>
            <button type="button" className="p-btn p-btn--secondary" disabled={changed.length === 0} onClick={() => void save()}>
              {changed.length > 0 ? `Save ${changed.length} ${changed.length === 1 ? "change" : "changes"}` : "Save"}
            </button>
            <button type="button" className="p-btn p-btn--primary" disabled={!check.ok || changed.length > 0} onClick={() => void publish()}>
              {publishLabel}
            </button>
          </>
        )}
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      {note && <Alert tone="info">{note}</Alert>}

      <div className="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_320px]">
        {check && (
          <aside className="admin-panel grid gap-1 lg:sticky lg:top-4 lg:order-last" aria-labelledby="quality-check">
            <h2 id="quality-check" style={{ font: "var(--t-title-s)" }}>
              Quality check
            </h2>
            <p className="mb-1 text-[13px]" style={{ color: "var(--ink-3)" }}>
              Must pass before publishing.
            </p>
            <Checks check={check} unexplained={unexplained} />
          </aside>
        )}
        <ol className="min-w-0">
          {items?.map((it) => {
            const value = edits[it.position] ?? it.explanation;
            return (
              <li key={it.position} className="grid gap-2 border-b py-3.5" style={{ borderColor: "var(--line)" }}>
                <p className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-[12px]" style={{ color: "var(--ink)" }}>
                    {two(it.position + 1)}
                  </span>
                  {it.speaker && <b className="text-[14px] font-semibold leading-[1.3]">{it.speaker}</b>}
                  <span className="p-tag-mono">ANSWER · {it.answer.toUpperCase()}</span>
                </p>
                {it.quote && <blockquote style={{ font: "var(--t-quote-s)" }}>“{it.quote}”</blockquote>}
                <TextField
                  multiline
                  rows={2}
                  maxLength={2000}
                  label={`Explanation for item ${two(it.position + 1)}, shown after a wrong answer`}
                  value={value}
                  onChange={(v) => setEdits((x) => ({ ...x, [it.position]: v }))}
                  error={value.trim() ? undefined : "Missing. Labellers see this when they get it wrong."}
                />
              </li>
            );
          })}
        </ol>
      </div>
    </>
  );
}

/** The API's quality check as verdicts: passes solid, fails dashed, each in words. */
function Checks({ check, unexplained }: { check: RoundCheck; unexplained: RoundItem[] }) {
  const passable = check.reasons.some((r) => SAID[1].test(r));
  const strategies = Object.entries(check.scores)
    .map(([s, v]) => `${STRATEGY_WORD[s] ?? s}: ${Math.round(v * check.items)} of ${check.items}`)
    .join(". ");
  const others = check.reasons.filter((r) => !SAID.some((re) => re.test(r)));
  return (
    <>
      <Verdict word={passable ? "Fails" : "Passes"} kind={passable ? "wrong" : "right"}>
        <p>
          <b className="font-semibold">A constant answer can&apos;t pass.</b> {strategies ? `${strategies}.` : "No items to answer."}
        </p>
      </Verdict>
      <Verdict word={check.missing ? "Fails" : "Passes"} kind={check.missing ? "wrong" : "right"}>
        <p>
          <b className="font-semibold">Every item has an explanation.</b> {check.items - check.missing} of {check.items}
          {unexplained.length > 0 && ` · ${unexplained.length === 1 ? "item" : "items"} ${unexplained.map((it) => two(it.position + 1)).join(", ")} ${unexplained.length === 1 ? "is" : "are"} missing one`}.
        </p>
      </Verdict>
      {others.map((r) => (
        <Verdict key={r} word="Fails" kind="wrong">
          <p>{r[0].toUpperCase() + r.slice(1)}.</p>
        </Verdict>
      ))}
    </>
  );
}
