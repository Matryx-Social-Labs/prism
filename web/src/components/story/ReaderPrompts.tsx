"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { Close } from "@/components/icons";
import { send } from "@/lib/analytics";
import { isShareMarker } from "@/lib/attribution";
import { RETURNING_COOKIE } from "@/lib/returning";

// What a story page asks of a reader, inline and never in their way (DESIGN.md:
// no popups; marketing audit 04 P2-3, 06 §2.1 and §2.3). Every answer is one
// word from a list, counted as a daily total (common/usage.py) — never a
// person, never the story, never free text.

const ORIENTED = "prism.oriented"; // localStorage: the new-reader note was closed
const HEARD_ASKED = "prism.heard"; // localStorage: "Where did you hear…" has been shown in this browser
const CHECK_SHOWN_AT = "prism.check.at"; // localStorage: when "Could you check…" was last shown
const DEPTH = "prism.depth"; // sessionStorage: this visit's stories read (UsageBeacon)
const CHECK_GAP_MS = 14 * 24 * 60 * 60 * 1000;

/** Mirrors common/usage.HEARD. */
export const HEARD: ReadonlyArray<readonly [string, string]> = [
  ["friend", "A friend or a group chat"],
  ["search", "Search"],
  ["ai", "An AI assistant"],
  ["x", "X / Twitter"],
  ["linkedin", "LinkedIn"],
  ["reddit", "Reddit"],
  ["newsletter", "A newsletter"],
  ["launch", "Product Hunt or a launch site"],
  ["other", "Somewhere else"],
];
/** Mirrors common/usage.SURVEY (as check:<word>). */
const CHECK: ReadonlyArray<readonly [string, string]> = [["yes", "Yes"], ["partly", "Partly"], ["no", "No"]];

type Ask = "heard" | "check";

/**
 * A first visit that came by a shared link: one line on what this page is,
 * with the way to the rest. Gone for good once closed, and never for a reader
 * who has reached the chart (the prism.returning cookie).
 */
export function ArrivalNote({ className = "" }: { className?: string }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      const shared = isShareMarker(new URLSearchParams(window.location.search).get("s"));
      const returning = document.cookie.split("; ").some((c) => c.startsWith(`${RETURNING_COOKIE}=`));
      setShow(shared && !returning && !localStorage.getItem(ORIENTED));
    } catch {
      /* storage blocked: no note, the record reads the same */
    }
  }, []);
  if (!show) return null;
  const close = () => {
    try {
      localStorage.setItem(ORIENTED, "1");
    } catch {
      /* it will show again next time; harmless */
    }
    setShow(false);
  };
  return (
    <div role="note" className={`p-alert p-alert--info items-center py-1.5 pr-1 ${className}`}>
      <p className="flex-1" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
        Prism keeps one record per news event from the outlets it monitors, with every quote checked against its article.{" "}
        <Link href="/feed" className="p-link whitespace-nowrap">Today&rsquo;s record →</Link>
      </p>
      <button type="button" onClick={close} aria-label="Close this note" className="inline-flex h-11 w-11 flex-none items-center justify-center" style={{ color: "var(--ink-3)" }}>
        <Close />
      </button>
    </div>
  );
}

/** Which question this page may ask, decided when the reader reaches it. */
function pick(): Ask | null {
  try {
    // "Where did you hear…": the 2nd story of a visit, once in this browser.
    if (sessionStorage.getItem(DEPTH) === "2" && !localStorage.getItem(HEARD_ASKED)) return "heard";
    // "Could you check…": one story, then not again for 14 days (which also makes it one per visit).
    const last = Number(localStorage.getItem(CHECK_SHOWN_AT) ?? 0);
    return Date.now() - last >= CHECK_GAP_MS ? "check" : null;
  } catch {
    return null; // storage blocked: without a memory, asking would nag
  }
}

function markShown(ask: Ask) {
  localStorage.setItem(ask === "heard" ? HEARD_ASKED : CHECK_SHOWN_AT, ask === "heard" ? "1" : String(Date.now()));
}

/**
 * The one question slot at the foot of the record, after the coverage. It
 * stays empty until the reader scrolls to it, then asks at most one thing:
 * where they heard of Prism (their 2nd story of a visit, once per browser), or
 * whether they could check this story for themselves (at most every 14 days).
 * Answering or "Not now" closes it.
 */
export function ReaderQuestion() {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  const [ask, setAsk] = useState<Ask | null>(null);
  const [state, setState] = useState<"open" | "answered" | "closed">("open");

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      io.disconnect();
      const next = pick();
      if (!next) return;
      try {
        markShown(next);
      } catch {
        return;
      }
      setAsk(next);
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const answer = (w: string) => {
    send(ask === "heard" ? "heard" : "survey", ask === "heard" ? w : `check:${w}`);
    setState("answered");
  };

  const open = ask && state === "open";
  return (
    // Never display:none while empty: a box that is not laid out never intersects.
    <div ref={ref}>
      {open && (
        <div role="group" aria-labelledby={id} className="mt-8 grid gap-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
          <p id={id} style={{ font: "var(--t-body)", fontWeight: 600 }}>
            {ask === "heard" ? "Where did you hear about Prism?" : "Could you check this story for yourself?"}
          </p>
          <div className="flex flex-wrap gap-2">
            {(ask === "heard" ? HEARD : CHECK).map(([w, label]) => (
              <button key={w} type="button" className="p-chip" onClick={() => answer(w)}>{label}</button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-x-4">
            <button type="button" className="p-btn p-btn--text px-0" onClick={() => setState("closed")}>Not now</button>
            <span style={{ font: "400 13px/1.4 var(--font-read)", color: "var(--ink-3)" }}>Counted as a total. Never linked to you.</span>
          </div>
        </div>
      )}
      {ask && state === "answered" && (
        <p role="status" className="mt-8 border-t pt-4" style={{ borderColor: "var(--line)", font: "var(--t-body-s)", color: "var(--ink-2)" }}>
          Thank you.
        </p>
      )}
    </div>
  );
}
