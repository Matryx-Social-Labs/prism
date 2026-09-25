"use client";

import { useEffect, useState } from "react";
import { ChartRow } from "@/components/ChartRow";
import { fetchFeed, type FeedItem } from "@/lib/api";

const ROWS = 3;
const DESKTOP = "(min-width: 1024px)";

/**
 * "Your record, as it will open" — the desktop column beside onboarding: the
 * three newest stories for the answers so far, from the same feed call For you
 * makes (interests + state, newest first), so it re-sorts as the reader answers.
 * Real rows or nothing: while loading it shows placeholders, on a failed call a
 * line that says so. Not fetched on a phone, where the column is not drawn.
 */
export function OnboardingPreview({ interests, state, subjects }: { interests: string[]; state: string | null; subjects: string[] }) {
  const [desktop, setDesktop] = useState(false);
  const [rows, setRows] = useState<FeedItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const key = `${interests.join(",")}|${state ?? ""}`;

  useEffect(() => setDesktop(window.matchMedia(DESKTOP).matches), []);

  useEffect(() => {
    if (!desktop) return;
    let live = true;
    setFailed(false);
    const [list, st] = key.split("|");
    fetchFeed({ interests: list ? list.split(",") : undefined, state: st || undefined, sort: "latest", limit: ROWS })
      .then((items) => live && setRows(items.slice(0, ROWS)))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [desktop, key]);

  if (!desktop) return null;
  const n = subjects.length;
  return (
    <aside className="hidden content-start gap-2.5 pt-10 lg:grid" aria-label="Your record, as it will open">
      <p className="p-eyebrow">Your record, as it will open</p>
      <p className="p-count">{`newest first · ${n ? `${n} ${n === 1 ? "subject" : "subjects"}` : "every subject"}`}</p>
      {failed ? (
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>The record could not be loaded just now. Your answers still count.</p>
      ) : rows === null ? (
        <div className="grid gap-2">
          {Array.from({ length: ROWS }, (_, i) => <span key={i} className="p-skel h-28" />)}
        </div>
      ) : (
        <ol className="p-print grid gap-2">
          {rows.map((it) => <ChartRow key={it.id} item={it} />)}
        </ol>
      )}
    </aside>
  );
}
