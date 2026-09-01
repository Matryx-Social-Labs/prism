"use client";

/**
 * Story-boundary labelling — one judgement per screen, for people without a checkout.
 *
 * The gold set decides every story-layer question, and it was 45 stories written by
 * hand into a Python file. This page is how it grows: a shareable link, a first
 * name, and a stack of one-question screens.
 *
 * DESIGN.md compliance, and the one place it constrains the obvious solution:
 * "Chrome is monochrome. Color only ever means a lens is speaking." A labelling UI
 * wants to paint chosen rows green — and that would be the only colour on the page,
 * spending the product's strongest signal on a checkbox. Selection is therefore
 * carried by a left rule, a filled marker and an ink-weight shift, which is the same
 * "status by line style, not colour" rule the Storyline Map already follows. Rules
 * and type, no cards (DESIGN.md, 2026-07-25). Mono is provenance only: dates, outlet
 * counts, and which proposer suggested a row.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchLabelBatch,
  fetchLabelTask,
  joinLabelBatch,
  postLabelAnswer,
  type LabelBatch,
  type LabelEvent,
  type LabelTask,
} from "@/lib/api";

const WHO_KEY = "prism.labeller";
// Per batch, because one person may be invited to several and each carries its own
// credential. Stored rather than put in the URL: a token in the address bar leaks
// through history, Referer headers and any shared screenshot.
const TOKEN_KEY = (batch: string) => `prism.label.token.${batch}`;

function provenance(e: LabelEvent): string {
  const bits = [
    e.at ? new Date(e.at).toLocaleDateString(undefined, { day: "2-digit", month: "short" }) : "—",
    `${e.source_count} ${e.source_count === 1 ? "outlet" : "outlets"}`,
  ];
  if (e.actors.length) bits.push(e.actors.slice(0, 3).join(" · "));
  return bits.join("  ·  ");
}

export default function LabelPage({ params }: { params: Promise<{ key: string }> }) {
  const [batchKey, setBatchKey] = useState("");
  const [who, setWho] = useState("");
  const [token, setToken] = useState("");
  const [draftWho, setDraftWho] = useState("");
  const [joinError, setJoinError] = useState("");
  const [batch, setBatch] = useState<LabelBatch | null>(null);
  const [task, setTask] = useState<LabelTask | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [state, setState] = useState<"loading" | "ready" | "done" | "closed" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const startedAt = useRef<number>(Date.now());

  useEffect(() => {
    params.then((p) => setBatchKey(p.key));
  }, [params]);

  // The name is remembered so someone resuming tomorrow is served the tasks they
  // have not done, rather than starting over as a stranger.
  //
  // An invited labeller arrives as /label/<batch>#<token>. THE FRAGMENT IS WHY:
  // browsers never send it to the server, so a named credential does not appear
  // in access logs, in a Referer header, or in an upstream proxy's history the way
  // a path or query segment would. It is claimed into localStorage on arrival and
  // then stripped from the address bar, so a shared screenshot of a working
  // session carries nothing either.
  //
  // Without this the invite path was silently dead: `tools/gold_candidates.py
  // invite` printed these URLs, the page ignored the fragment, and the person fell
  // through to the join form and self-joined as a stranger — so the named identity
  // that was minted for them was never the one their answers were recorded under.
  useEffect(() => {
    if (!batchKey) return;
    try {
      const invited = window.location.hash.replace(/^#/, "").trim();
      if (invited) {
        window.localStorage.setItem(TOKEN_KEY(batchKey), invited);
        window.history.replaceState(null, "", window.location.pathname);
        setToken(invited);
      }
      const savedTok = invited || window.localStorage.getItem(TOKEN_KEY(batchKey));
      const savedWho = window.localStorage.getItem(WHO_KEY);
      if (savedTok) setToken(savedTok);
      if (savedWho) setWho(savedWho);
    } catch {
      /* private mode: the session simply is not remembered */
    }
  }, [batchKey]);

  const load = useCallback(async () => {
    if (!batchKey || !token) return;
    setState("loading");
    try {
      const [b, t] = await Promise.all([
        fetchLabelBatch(batchKey, token),
        fetchLabelTask(batchKey, token),
      ]);
      setBatch(b);
      // The server knows who this credential belongs to; localStorage only knows
      // what someone last typed. An invited labeller has a name bound to their
      // invite before they ever open the link, so the server's answer wins — the
      // greeting must not be able to disagree with the name their answers are
      // recorded under.
      if (b.labeller) setWho(b.labeller);
      setPicked(new Set());
      startedAt.current = Date.now();
      if (t.closed) setState("closed");
      else if (!t.task) {
        setTask(null);
        setState("done");
      } else {
        setTask(t.task);
        setState("ready");
      }
    } catch {
      setState("error");
    }
  }, [batchKey, token]);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = useCallback(
    async (unsure: boolean) => {
      if (!task || saving) return;
      setSaving(true);
      try {
        await postLabelAnswer(batchKey, {
          task_id: task.id,
          token,
          selected: [...picked],
          unsure,
          ms_spent: Date.now() - startedAt.current,
        });
        await load();
      } catch {
        setState("error");
      } finally {
        setSaving(false);
      }
    },
    [task, saving, batchKey, token, picked, load]
  );

  const toggle = useCallback((id: string) => {
    setPicked((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }, []);

  // Number keys toggle, Enter submits. Labelling is repetitive by nature and the
  // hand should not leave the keyboard for a hundred screens.
  useEffect(() => {
    if (state !== "ready" || !task) return;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      const target = ev.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if (ev.key === "Enter") {
        ev.preventDefault();
        void submit(false);
        return;
      }
      const n = Number(ev.key);
      if (Number.isInteger(n) && n >= 1 && n <= task.candidates.length) {
        ev.preventDefault();
        toggle(task.candidates[n - 1].id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, task, submit, toggle]);

  const pct = useMemo(
    () => (batch && batch.total ? Math.round((batch.done / batch.total) * 100) : 0),
    [batch]
  );

  if (!token) {
    return (
      <Shell>
        <h1 className="text-[30px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          Help us teach Prism what one story is
        </h1>
        <p className="mt-3 max-w-[52ch] text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
          You&apos;ll see a headline, then a few others from around the same time. Tick the
          ones covering the <strong>same unfolding story</strong>. It takes about a minute
          each, and you can stop whenever you like.
        </p>
        <form
          className="mt-8 flex flex-wrap items-center gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            const name = draftWho.trim();
            if (!name) return;
            try {
              // The credential is minted here, once. The name is only a caption —
              // two labellers may share one and stay separate identities.
              const t = await joinLabelBatch(batchKey, name);
              try {
                window.localStorage.setItem(TOKEN_KEY(batchKey), t);
                window.localStorage.setItem(WHO_KEY, name);
              } catch {
                /* not remembering is survivable; the session still works */
              }
              setWho(name);
              setToken(t);
            } catch {
              // The name screen returns early, so the shared error state below is
              // never reached from here — without this the person clicks Start and
              // nothing at all happens.
              setJoinError("Something went wrong. Check the link and try again.");
            }
          }}
        >
          <input
            value={draftWho}
            onChange={(e) => setDraftWho(e.target.value)}
            placeholder="Your first name"
            maxLength={60}
            aria-label="Your first name"
            className="h-11 rounded-full border bg-transparent px-4 text-[14.5px] outline-none"
            style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
          />
          <button
            type="submit"
            className="h-11 rounded-full px-5 text-[14.5px] font-medium"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            Start
          </button>
        </form>
        {joinError && (
          <p role="alert" className="mt-4 text-[14.5px]" style={{ color: "var(--danger)" }}>
            {joinError}
          </p>
        )}
        <p className="mt-4 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
          YOUR NAME IS ONLY USED TO REMEMBER WHERE YOU GOT TO
        </p>
      </Shell>
    );
  }

  return (
    <Shell>
      <header
        // NOT sticky. It was, and on a phone it sat underneath the global brand
        // header — the progress rule showed through while the batch name and count
        // were hidden behind it. Stickiness bought nothing here anyway: a task is
        // one screen, and submitting returns to the top, so the count is in view at
        // the start of every question regardless.
        className="-mx-5 mb-8 border-b px-5 py-3 sm:-mx-8 sm:px-8"
        style={{ borderColor: "var(--line)" }}
      >
        <div className="flex items-baseline justify-between gap-4">
          <span className="text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            {batch?.name ?? "Labelling"}
          </span>
          <span className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            {batch ? `${String(batch.done).padStart(3, "0")} / ${batch.total}` : "—"}
          </span>
        </div>
        <div className="mt-2 h-px w-full" style={{ background: "var(--line)" }}>
          <div
            className="h-px motion-reduce:transition-none"
            style={{ width: `${pct}%`, background: "var(--ink)", transition: "width 250ms ease-out" }}
          />
        </div>
      </header>

      {state === "loading" && <Note>Loading…</Note>}
      {state === "error" && (
        <Note>
          Something went wrong.{" "}
          <button className="underline" onClick={() => void load()}>
            Try again
          </button>
        </Note>
      )}
      {state === "closed" && <Note>This batch is closed. Thank you.</Note>}
      {state === "done" && (
        <Note>
          That&apos;s everything — {batch?.total ?? 0} judgements. Thank you, {who}.
        </Note>
      )}

      {state === "ready" && task && (
        <>
          <p className="font-mono text-[10.5px] uppercase" style={{ color: "var(--ink-faint)" }}>
            {task.sector ?? "news"} · question {task.position + 1}
          </p>
          <h1
            className="mt-2 text-[23px] leading-[1.3]"
            style={{ fontFamily: "var(--font-display), serif", textWrap: "pretty" }}
          >
            {task.seed.title}
          </h1>
          <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            {provenance(task.seed)}
          </p>

          <p className="mt-8 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            Which of these are part of the same unfolding story?
          </p>

          <ul className="mt-3">
            {task.candidates.map((c, i) => {
              const on = picked.has(c.id);
              return (
                <li key={c.id} style={{ borderTop: "1px solid var(--line)" }}>
                  <button
                    type="button"
                    onClick={() => toggle(c.id)}
                    aria-pressed={on}
                    className="flex w-full items-start gap-3 py-3 text-left motion-reduce:transition-none"
                    style={{
                      // Selection is a RULE and ink weight, never a colour fill —
                      // colour is reserved for lenses (DESIGN.md, the colour rule).
                      boxShadow: on ? "inset 2px 0 0 0 var(--ink)" : "none",
                      paddingLeft: on ? 12 : 0,
                      transition: "padding-left 150ms ease-out",
                    }}
                  >
                    <span
                      aria-hidden
                      className="mt-[3px] inline-block h-3 w-3 shrink-0 rounded-full border"
                      style={{
                        borderColor: on ? "var(--ink)" : "var(--line-strong)",
                        background: on ? "var(--ink)" : "transparent",
                      }}
                    />
                    <span className="min-w-0">
                      <span
                        className="block text-[15.5px] leading-snug"
                        style={{
                          color: on ? "var(--ink)" : "var(--ink-muted)",
                          fontWeight: on ? 600 : 400,
                        }}
                      >
                        {c.title}
                      </span>
                      <span
                        className="mt-1 block font-mono text-[10.5px]"
                        style={{ color: "var(--ink-faint)" }}
                      >
                        {provenance(c)}
                        {c.signals.length ? `  ·  ${c.signals.join("+")}` : ""}
                      </span>
                    </span>
                    <span
                      aria-hidden
                      className="ml-auto shrink-0 font-mono text-[10.5px]"
                      style={{ color: "var(--ink-faint)" }}
                    >
                      {i + 1}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div
            className="mt-6 flex flex-wrap items-center gap-3 border-t pt-5"
            style={{ borderColor: "var(--line)" }}
          >
            <button
              type="button"
              disabled={saving}
              onClick={() => void submit(false)}
              className="h-11 rounded-full px-5 text-[14.5px] font-medium disabled:opacity-50"
              style={{ background: "var(--ink)", color: "var(--bg)" }}
            >
              {picked.size ? `Yes — ${picked.size} selected` : "None of these"}
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={() => void submit(true)}
              className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              Not sure
            </button>
            <span className="font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
              KEYS 1–{task.candidates.length} TOGGLE · ENTER SUBMITS
            </span>
          </div>

          <p className="mt-6 text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            Same topic isn&apos;t enough — two different court cases about one law are two
            stories. <strong>Not sure</strong> is a real answer; it keeps genuinely hard
            calls out of the training data rather than guessing at them.
          </p>
        </>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  // 720px is DESIGN.md's onboarding/interests measure. This is a focused
  // single-decision surface, not a reading river.
  return (
    <main className="mx-auto min-h-dvh w-full max-w-[720px] px-5 pb-24 pt-6 sm:px-8">
      {children}
    </main>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-16 text-[15.5px]" style={{ color: "var(--ink-muted)" }}>
      {children}
    </p>
  );
}
