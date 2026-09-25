"use client";

/**
 * Labelling — one judgement per screen, for people without a checkout.
 *
 * The gold set decides every story-layer question, and it was 45 stories written by
 * hand into a Python file. This page is how it grows: a shareable link, a first
 * name, and a stack of one-question screens.
 *
 * Design System v2 · Label flow board: a sticky task header (the way back, the
 * batch, which question this is), the question as the eyebrow, the material, and
 * the answers — in a bar at the thumb on a phone, beside the material with their
 * keys on desktop. Every kind of task — story, claim, quote rendering, brief line
 * — sits in the same frame (components/label/parts.TaskFrame). The guide before
 * the first task, the named-invite greeting, the self-join form and every end
 * state stand alone under the label bar, each with a way back to the workspace.
 * Selection and verdicts are rule weight, a filled mark and a word, never colour
 * alone; mono is provenance only.
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
  type LabelFeedback,
  type LabelGuide,
  type LabelResult,
  type LabelTask,
} from "@/lib/api";
import { Alert, TextField } from "@/components/ui";
import { GuideFailed, GuideLoading, GuidePrimer } from "@/components/label/GuideView";
import {
  BackToWorkspace, Column, EndScreen, LabelStrip, Lede, Small, TaskHeader, Title, type Answer,
} from "@/components/label/parts";
import { DoneScreen, PracticeFeedback, RoundResult } from "@/components/label/rounds";
import { ClaimTask } from "@/components/label/ClaimTask";
import { QuoteRenderingTask } from "@/components/label/QuoteRenderingTask";
import { BriefLineTask } from "@/components/label/BriefLineTask";
import { StoryTask } from "@/components/label/StoryTask";
import { KIND_QUESTION } from "@/lib/labeller";

const WHO_KEY = "prism.labeller";
// Per batch, because one person may be invited to several and each carries its own
// credential. Stored rather than put in the URL: a token in the address bar leaks
// through history, Referer headers and any shared screenshot.
const TOKEN_KEY = (batch: string) => `prism.label.token.${batch}`;
// Per batch, not global: someone who read the story primer has not been taught
// the claim task, and the two ask for opposite kinds of judgement.
const PRIMER_KEY = (batch: string) => `prism.label.primer.${batch}`;

type State = "loading" | "ready" | "done" | "closed" | "result" | "requalify" | "blocked" | "error";

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
  const [state, setState] = useState<State>("loading");
  // Practice only: the answer to the question just answered, shown until "Next".
  const [feedback, setFeedback] = useState<LabelFeedback | null>(null);
  // Practice or test: the score, once every question in the round is answered.
  const [result, setResult] = useState<LabelResult | null>(null);
  const [saving, setSaving] = useState(false);
  // Which answer is being saved: that button says so.
  const [pending, setPending] = useState<Answer | null>(null);
  // Arrived this visit on a founder's named link (/label/<key>#token): greeted
  // by name before the first question.
  const [invited, setInvited] = useState(false);
  const [greeted, setGreeted] = useState(false);
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
        setInvited(true);
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
      setState(e instanceof Error && e.message === "403" ? "blocked" : "error");
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
        setState(e instanceof Error && e.message === "403" ? "blocked" : "error");
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
  const greeting = invited && !greeted && state === "ready";
  const candidateTask = state === "ready" && !!task && !task.claim && !task.rendering && !task.line && primed !== false && !feedback && !greeting;
  useEffect(() => {
    if (!candidateTask || !task) return;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      const target = ev.target as HTMLElement | null;
      if (target && (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable)) return;
      if (ev.key === "Enter") {
        const control = target?.closest("button, a, summary");
        if (control && !control.hasAttribute("data-candidate")) return;
        // Yes waits for a tick: with nothing ticked, Enter is not "None".
        if (picked.size === 0) return;
        ev.preventDefault();
        setPending("yes");
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
  }, [candidateTask, task, picked, submit, toggle]);


  const answer = (a: Answer) => {
    setPending(a);
    void submit(a === "unsure", a === "cant", a === "yes");
  };
  // The tick tasks: "yes" files the ticked rows, "no" is an explicit None.
  const answerStory = (a: Answer) => {
    setPending(a);
    void submit(a === "unsure", a === "cant", false, a === "no");
  };

  if (!token) {
    return (
      <Screen>
        <Title>Help us teach Prism what one story is</Title>
        <Lede>
          You&apos;ll see a headline, then a few others from around the same time. Tick the
          ones covering the <strong style={{ color: "var(--ink)" }}>same unfolding story</strong>. It takes about a minute
          each, you can stop whenever you like, and no account is needed.
        </Lede>
        <form
          className="grid gap-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const name = draftWho.trim();
            if (!name) return;
            setJoinError("");
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
          <TextField
            label="Your first name"
            hint="Your name is only used to remember where you got to."
            value={draftWho}
            onChange={setDraftWho}
            maxLength={60}
            autoComplete="given-name"
          />
          {joinError && <Alert tone="error">{joinError}</Alert>}
          <div>
            <button type="submit" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto" disabled={!draftWho.trim()}>
              Start
            </button>
          </div>
        </form>
        {/* No guide here: this screen is reached by anyone holding the batch
            link, before they have a credential, and the guide goes only to a
            credential (founder, 2026-09-23). It is the first thing shown once
            they have joined. */}
      </Screen>
    );
  }

  // The end of a batch, of a round, or of being let in: each stands alone, with
  // its own way back.
  if (state === "done") {
    return (
      <Screen>
        <DoneScreen total={batch?.total ?? 0} batch={batch?.name} who={who} />
      </Screen>
    );
  }
  if (state === "result" && result) {
    return (
      <Screen>
        <RoundResult result={result} kind={batch?.kind} />
      </Screen>
    );
  }
  if (state === "closed") {
    const done = batch?.done ?? 0;
    return (
      <Screen>
        <EndScreen title="This batch has closed.">
          <Lede>
            It no longer takes answers.
            {done > 0 && <> Your <span className="font-mono">{done}</span> {done === 1 ? "judgement is" : "judgements are"} kept.</>}
          </Lede>
        </EndScreen>
      </Screen>
    );
  }
  if (state === "requalify" || state === "blocked") {
    return (
      <Screen>
        <EndScreen
          dashed
          title="You can't label this batch right now."
          action={<div><BackButton /></div>}
        >
          <Lede>
            {state === "requalify"
              ? "Your recent answers on the checks hidden in the work fell below the bar, so this kind of task is closed to you for now. To work on it again, take this task's test again from your workspace."
              : "Either your recent answers on the checks hidden in the work fell below the bar — take this task's test again from your workspace — or your labelling was paused."}
          </Lede>
        </EndScreen>
      </Screen>
    );
  }

  // A founder's named invite: no account, no language gate — greeted by the name
  // on the invite, told how many questions, then on.
  if (greeting && batch) {
    const n = Math.min(batch.done + 1, batch.total);
    return (
      <Screen>
        <Title>{batch.labeller ? `Hello, ${batch.labeller}.` : "Hello."}</Title>
        <Lede>
          A founder asked you to answer <span className="font-mono">{batch.total}</span>{" "}
          {batch.total === 1 ? "question" : "questions"} in “{batch.name}”.
          {batch.done > 0 && <> You have answered <span className="font-mono">{batch.done}</span>.</>}
        </Lede>
        {batch.kind && KIND_QUESTION[batch.kind] && (
          <div className="p-card grid gap-1">
            <p style={{ font: "600 15px/1.3 var(--font-read)" }}>{KIND_QUESTION[batch.kind]}</p>
            <Small>One question at a time, about a minute each. You can stop and come back to this link.</Small>
          </div>
        )}
        <div>
          <button type="button" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto" onClick={() => setGreeted(true)}>
            {batch.done > 0 ? "Continue" : "Start"} · question {n} of {batch.total}
          </button>
        </div>
      </Screen>
    );
  }

  // The guide, read before the first task of this batch.
  if (state === "ready" && task && primed === false) {
    return (
      <Screen>
        {guide ? (
          <GuidePrimer
            guide={guide}
            context={batch?.name ? <p className="p-eyebrow">Before your first task in {batch.name}</p> : undefined}
            back={<BackToWorkspace />}
            onStart={() => {
              try {
                window.localStorage.setItem(PRIMER_KEY(batchKey), "1");
              } catch {
                // Storage denied — still let them through; the primer has been read.
              }
              setPrimed(true);
            }}
          />
        ) : guideFailed ? (
          <GuideFailed onRetry={() => setGuideTry((n) => n + 1)} />
        ) : (
          <GuideLoading />
        )}
      </Screen>
    );
  }

  const tag = batch?.purpose === "practice" ? "Practice" : batch?.purpose === "qualify" ? "Test" : undefined;
  const busy = saving ? pending : null;
  const shown = state === "ready" && task && primed !== false ? task : null;
  const practice = shown && feedback ? <PracticeFeedback task={shown} feedback={feedback} onNext={() => void load()} /> : undefined;

  return (
    <div className="flex min-h-dvh w-full flex-col">
      <TaskHeader batch={batch?.name ?? "Labelling"} done={batch?.done} total={batch?.total} />
      {state === "loading" && (
        <div className="mx-auto grid w-full max-w-[680px] gap-3 px-4 pt-6" role="status" aria-busy="true">
          <span className="p-skel h-3 w-40" />
          <span className="p-skel h-[120px]" />
          <span className="p-skel h-16" />
          <span className="p-skel h-16" />
          <span className="sr-only">Loading…</span>
        </div>
      )}
      {state === "error" && (
        <div className="mx-auto w-full max-w-[680px] px-4 pt-6">
          <Alert
            tone="error"
            title="Something went wrong."
            action={
              <button type="button" className="p-btn p-btn--secondary p-btn--sm min-h-11 lg:min-h-9" onClick={() => void load()}>
                Try again
              </button>
            }
          >
            Prism did not answer. Your earlier answers are saved.
          </Alert>
        </div>
      )}
      {shown &&
        (shown.line ? (
          <BriefLineTask line={shown.line} tag={tag} saving={saving} pending={busy} feedback={practice} onAnswer={answer} />
        ) : shown.rendering ? (
          <QuoteRenderingTask rendering={shown.rendering} tag={tag} saving={saving} pending={busy} feedback={practice} onAnswer={answer} />
        ) : shown.claim ? (
          <ClaimTask
            claim={shown.claim}
            position={shown.position}
            tag={tag}
            saving={saving}
            pending={busy}
            decide={guide?.decide}
            feedback={practice}
            onAnswer={answer}
          />
        ) : (
          <StoryTask
            task={shown}
            kind={batch?.kind}
            tag={tag}
            picked={picked}
            saving={saving}
            pending={busy}
            decide={guide?.decide}
            feedback={practice}
            onToggle={toggle}
            onAnswer={answerStory}
          />
        ))}
    </div>
  );
}

/** A label screen that is not a task: the label bar, then the column. */
function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh w-full flex-col">
      <LabelStrip />
      <Column>{children}</Column>
    </div>
  );
}

function BackButton() {
  return (
    <Link href="/label" className="p-btn p-btn--ghost p-btn--lg w-full lg:w-auto">
      Back to your workspace
    </Link>
  );
}
