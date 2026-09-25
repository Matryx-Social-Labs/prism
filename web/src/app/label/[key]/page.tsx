"use client";

/**
 * Labelling — one judgement per screen, for people without a checkout.
 *
 * The gold set decides every story-layer question, and it was 45 stories written by
 * hand into a Python file. This page is how it grows: a shareable link, a first
 * name, and a stack of one-question screens.
 *
 * Design System v2 · labeller Task: a sticky task header (the way back, the batch,
 * this labeller's count), the question as the eyebrow, the task, and a sticky
 * answer footer. Every kind of task — story, claim, quote rendering, brief line —
 * uses the same parts (components/label/parts). Selection and verdicts are rule
 * weight, a filled mark and a word, never colour alone; mono is provenance only.
 */

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchLabelBatch,
  fetchLabelGuide,
  fetchLabelTask,
  joinLabelBatch,
  postLabelAnswer,
  type LabelBatch,
  type LabelClaim,
  type LabelFeedback,
  type LabelGuide,
  type LabelResult,
  type LabelTask,
} from "@/lib/api";
import { GuidePrimer, HowToDecide } from "@/components/label/GuideView";
import { AnswerButtons, LabelStrip, QuoteInContext, TaskHeader } from "@/components/label/parts";
import { DoneScreen, PracticeFeedback, RoundResult } from "@/components/label/rounds";
import { QuoteRenderingTask } from "@/components/label/QuoteRenderingTask";
import { BriefLineTask } from "@/components/label/BriefLineTask";
import { StoryTask } from "@/components/label/StoryTask";

const WHO_KEY = "prism.labeller";
// Per batch, because one person may be invited to several and each carries its own
// credential. Stored rather than put in the URL: a token in the address bar leaks
// through history, Referer headers and any shared screenshot.
const TOKEN_KEY = (batch: string) => `prism.label.token.${batch}`;
// Per batch, not global: someone who read the story primer has not been taught
// the claim task, and the two ask for opposite kinds of judgement.
const PRIMER_KEY = (batch: string) => `prism.label.primer.${batch}`;

type Verdict = "yes" | "no" | "unsure" | "skip";

/** The claim task: a quote, where it sits in the article, and who the extractor
 *  says said it.
 *
 *  THE VERBATIM CHECK CANNOT DECIDE THIS. A sentence can be copied exactly from
 *  the article and still be put in the wrong mouth — the quote matches, the
 *  attribution is a lie, and nothing downstream can tell. That is why a person
 *  reads it.
 *
 *  The quote is shown INSIDE its surrounding sentences rather than alone,
 *  because the attribution usually lives in the words either side of it ("said
 *  the minister", "according to Kaspersky"). Shown alone the question would be
 *  unanswerable and the labeller would be guessing. */
function ClaimTask({
  claim, position, saving, onAnswer, decide,
}: {
  claim: LabelClaim;
  position: number;
  saving: boolean;
  onAnswer: (verdict: Verdict) => void;
  decide?: LabelGuide["decide"];
}) {
  return (
    <>
      <h1 className="p-eyebrow">Who said this?</h1>
      <div className="p-card grid gap-1.5">
        <h2 style={{ font: "var(--t-title)", textWrap: "pretty", overflowWrap: "anywhere" }}>{claim.title}</h2>
        <p className="p-count">{claim.source}</p>
      </div>

      <p style={{ font: "var(--t-body)" }}>
        Does this article attribute the highlighted words to <strong>{claim.speaker}</strong>?
      </p>

      {claim.lead ? (
        <div className="grid gap-1">
          <h2 className="p-eyebrow">How the article opens</h2>
          <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{claim.lead}…</p>
        </div>
      ) : null}

      <QuoteInContext before={claim.context_before} quote={claim.quote_text} after={claim.context_after} />

      {claim.article_text ? (
        <details>
          <summary className="flex min-h-11 cursor-pointer list-none items-center text-[14px] font-semibold [&::-webkit-details-marker]:hidden" style={{ color: "var(--accent)" }}>
            Read the whole article
          </summary>
          <p className="max-h-[420px] overflow-y-auto whitespace-pre-line" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
            {claim.article_text}
          </p>
        </details>
      ) : null}

      {/* Open on the FIRST question only. A claims labeller arrives with an
          invite token, which skips the landing screen where the story flow
          shows its guide open — so collapsed here meant the guide was never put
          in front of anyone. The point of it is being read BEFORE the first
          judgement, not after a wrong one. */}
      {decide && <HowToDecide blocks={decide.blocks} closing={decide.closing} open={position === 0} />}

      <AnswerButtons
        yes={`Yes — ${claim.speaker.slice(0, 24)} said it`}
        no="No — someone else, or nobody"
        cantRead="Can't read this"
        saving={saving}
        onYes={() => onAnswer("yes")}
        onNo={() => onAnswer("no")}
        onUnsure={() => onAnswer("unsure")}
        onCantRead={() => onAnswer("skip")}
      />
    </>
  );
}

export default function LabelPage({ params }: { params: Promise<{ key: string }> }) {
  const [batchKey, setBatchKey] = useState("");
  const [who, setWho] = useState("");
  const [token, setToken] = useState("");
  const [draftWho, setDraftWho] = useState("");
  const [joinError, setJoinError] = useState("");
  const [batch, setBatch] = useState<LabelBatch | null>(null);
  // Null until read from storage, so the first paint does not flash the primer at
  // someone who has already dismissed it.
  const [primed, setPrimed] = useState<boolean | null>(null);
  const [task, setTask] = useState<LabelTask | null>(null);
  // The guide for this batch's kind, from the API with this batch's invite —
  // never from the site's JavaScript (common/label_guides.py).
  const [guide, setGuide] = useState<LabelGuide | null>(null);
  const [guideFailed, setGuideFailed] = useState(false);
  const [guideTry, setGuideTry] = useState(0);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [state, setState] = useState<"loading" | "ready" | "done" | "closed" | "result" | "requalify" | "error">("loading");
  // Practice only: the answer to the question just answered, shown until "Next".
  const [feedback, setFeedback] = useState<LabelFeedback | null>(null);
  // Practice or test: the score, once every question in the round is answered.
  const [result, setResult] = useState<LabelResult | null>(null);
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
      try {
        setPrimed(window.localStorage.getItem(PRIMER_KEY(batchKey)) === "1");
      } catch {
        // Private browsing with storage denied: show the primer rather than
        // skipping it. Reading it twice costs two minutes; skipping it cost 30%
        // disagreement last round.
        setPrimed(false);
      }
      const savedTok = invited || window.localStorage.getItem(TOKEN_KEY(batchKey));
      const savedWho = window.localStorage.getItem(WHO_KEY);
      if (savedTok) setToken(savedTok);
      if (savedWho) setWho(savedWho);
    } catch {
      /* private mode: the session simply is not remembered */
    }
  }, [batchKey]);

  useEffect(() => {
    if (!batchKey || !token) return;
    let live = true;
    setGuideFailed(false);
    fetchLabelGuide(batchKey, token)
      .then((g) => live && setGuide(g))
      .catch(() => live && setGuideFailed(true));
    return () => {
      live = false;
    };
  }, [batchKey, token, guideTry]);

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
      setFeedback(null);
      startedAt.current = Date.now();
      if (t.closed) setState("closed");
      else if (t.result) {
        setTask(null);
        setResult(t.result);
        setState("result");
      } else if (!t.task) {
        setTask(null);
        setState("done");
      } else {
        setTask(t.task);
        setState("ready");
      }
    } catch (e) {
      // 403 on a work batch: this account no longer holds the kind (live
      // checks withdrew it) or was paused — a reason to go back, not a glitch.
      setState(e instanceof Error && e.message === "403" ? "requalify" : "error");
    }
  }, [batchKey, token]);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = useCallback(
    async (unsure: boolean, skipped = false, agreed = false, none = false) => {
      if (!task || saving) return;
      setSaving(true);
      try {
        const res = await postLabelAnswer(batchKey, {
          task_id: task.id,
          token,
          // A skip carries no opinion, so whatever was ticked is discarded rather
          // than filed as a judgement nobody meant to give. "None of these" is an
          // explicit empty answer, whatever was ticked before it was pressed.
          // A claim answer has no candidate ids. "The article does attribute this
          // quote to this speaker" is carried as a single sentinel selection, so
          // the same responses table and the same agreement maths serve both kinds.
          selected: skipped || none ? [] : task.claim || task.rendering || task.line ? (agreed ? [task.id] : []) : [...picked],
          unsure,
          skipped,
          ms_spent: Date.now() - startedAt.current,
        });
        // A practice answer is marked straight away and waits for "Next";
        // everything else moves on.
        if (res?.feedback) setFeedback(res.feedback);
        else if (res?.requalify) setState("requalify");
        else await load();
      } catch (e) {
        // The same reading as load(): a 403 here means the kind was withdrawn
        // or the labeller paused between fetching this task and answering it.
        setState(e instanceof Error && e.message === "403" ? "requalify" : "error");
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
  //
  // Only while a candidate task is what is on screen: not under the guide, not
  // under a practice answer, and never on a claim or rendering task, which
  // advertise no shortcut. And Enter on a focused control answers as that
  // control — a window-wide Enter used to cancel "Yes" and file "No", and file
  // the ticked rows for a focused "Not sure" (2026-09-24). A candidate row is
  // the exception: Enter there submits, rather than unticking what was ticked.
  const candidateTask = state === "ready" && !!task && !task.claim && !task.rendering && !task.line && primed !== false && !feedback;
  useEffect(() => {
    if (!candidateTask || !task) return;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      const target = ev.target as HTMLElement | null;
      if (target && (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable)) return;
      if (ev.key === "Enter") {
        const control = target?.closest("button, a, summary");
        if (control && !control.hasAttribute("data-candidate")) return;
        ev.preventDefault();
        void submit(false);
        return;
      }
      const n = Number(ev.key);
      if (Number.isInteger(n) && n >= 1 && n <= (task.candidates?.length ?? 0)) {
        ev.preventDefault();
        toggle((task.candidates ?? [])[n - 1].id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [candidateTask, task, submit, toggle]);

  const answer = (verdict: Verdict) => void submit(verdict === "unsure", verdict === "skip", verdict === "yes");

  if (!token) {
    return (
      <Shell padded>
        <LabelStrip />
        <h1 className="mt-8" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>
          Help us teach Prism what one story is
        </h1>
        <p className="mt-3 max-w-[52ch]" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
          You&apos;ll see a headline, then a few others from around the same time. Tick the
          ones covering the <strong style={{ color: "var(--ink)" }}>same unfolding story</strong>. It takes about a minute
          each, and you can stop whenever you like.
        </p>
        <form
          className="mt-8 flex max-w-[480px] flex-wrap items-end gap-3"
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
          <label className="p-field min-w-0 flex-[1_1_220px]">
            <span className="p-field__label">Your first name</span>
            <input
              value={draftWho}
              onChange={(e) => setDraftWho(e.target.value)}
              maxLength={60}
              autoComplete="given-name"
              className="p-input"
            />
          </label>
          <button type="submit" className="p-btn p-btn--primary" style={{ minHeight: 48 }}>
            Start
          </button>
        </form>
        {joinError && (
          <p role="alert" className="p-field__error mt-3">
            {joinError}
          </p>
        )}
        <p className="mt-3" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          Your name is only used to remember where you got to.
        </p>
        {/* No guide here any more: this screen is reached by anyone holding the
            batch link, before they have a credential, and the guide goes only
            to a credential (founder, 2026-09-23). It is the first thing shown
            once they have joined. */}
      </Shell>
    );
  }

  // The end of a batch and the end of a round stand alone, with their own way back.
  if (state === "done") {
    return (
      <Shell padded>
        <DoneScreen total={batch?.total ?? 0} who={who} />
      </Shell>
    );
  }
  if (state === "result" && result) {
    return (
      <Shell padded>
        <RoundResult result={result} />
      </Shell>
    );
  }

  return (
    <Shell>
      <TaskHeader batch={batch?.name ?? "Labelling"} done={batch?.done} total={batch?.total} />
      <div className="flex flex-1 flex-col gap-4 px-4 pt-5">
        {state === "loading" && <Note>Loading…</Note>}
        {state === "error" && (
          <div role="alert" className="p-alert p-alert--error mt-6">
            <span>
              Something went wrong.{" "}
              <button type="button" className="p-link" onClick={() => void load()}>
                Try again
              </button>
            </span>
          </div>
        )}
        {state === "closed" && <Note>This batch is closed. Thank you.</Note>}
        {state === "requalify" && (
          <div className="p-alert p-alert--info mt-6">
            <p>
              You can&apos;t label this batch right now. Either your recent answers on the check questions hidden in the
              work fell below 80% — take this task&apos;s test again — or your labelling was paused.{" "}
              <Link className="p-link" href="/label">Open your workspace</Link>
            </p>
          </div>
        )}
        {state === "ready" && task && feedback && (
          <PracticeFeedback task={task} feedback={feedback} onNext={() => void load()} />
        )}

        {state === "ready" && task && primed === false && !guide && !guideFailed && (
          <Note>Loading the guide for this task.</Note>
        )}
        {state === "ready" && task && primed === false && !guide && guideFailed && (
          <div className="grid justify-items-start gap-4">
            <Note>The guide for this task could not be loaded. Read it before you start.</Note>
            <button type="button" className="p-btn p-btn--secondary" onClick={() => setGuideTry((n) => n + 1)}>
              Try again
            </button>
          </div>
        )}
        {state === "ready" && task && primed === false && guide && (
          <GuidePrimer
            guide={guide}
            onStart={() => {
              try {
                window.localStorage.setItem(PRIMER_KEY(batchKey), "1");
              } catch {
                // Storage denied — still let them through; the primer has been read.
              }
              setPrimed(true);
            }}
          />
        )}

        {state === "ready" && task && primed !== false && !feedback && (
          task.line ? (
            <BriefLineTask line={task.line} saving={saving} onAnswer={answer} />
          ) : task.rendering ? (
            <QuoteRenderingTask rendering={task.rendering} saving={saving} onAnswer={answer} />
          ) : task.claim ? (
            <ClaimTask claim={task.claim} position={task.position} saving={saving} decide={guide?.decide} onAnswer={answer} />
          ) : (
            <StoryTask
              task={task}
              kind={batch?.kind}
              picked={picked}
              saving={saving}
              decide={guide?.decide}
              onToggle={toggle}
              onAnswer={(a) => void submit(a === "unsure", a === "skip", false, a === "none")}
            />
          )
        )}
      </div>
    </Shell>
  );
}

function Shell({ children, padded = false }: { children: React.ReactNode; padded?: boolean }) {
  // 720px: a focused single-decision surface, not a reading river. The layout
  // already provides <main>; this is the column.
  return (
    <div className={`mx-auto flex min-h-dvh w-full max-w-[720px] flex-col ${padded ? "px-4 pb-24 pt-6" : ""}`}>
      {children}
    </div>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-10" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
      {children}
    </p>
  );
}
