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
  type LabelClaim,
  type LabelEvent,
  type LabelTask,
} from "@/lib/api";

const WHO_KEY = "prism.labeller";
// Per batch, because one person may be invited to several and each carries its own
// credential. Stored rather than put in the URL: a token in the address bar leaks
// through history, Referer headers and any shared screenshot.
const TOKEN_KEY = (batch: string) => `prism.label.token.${batch}`;
// Per batch, not global: someone who read the story primer has not been taught
// the claim task, and the two ask for opposite kinds of judgement.
const PRIMER_KEY = (batch: string) => `prism.label.primer.${batch}`;

function provenance(e: LabelEvent): string {
  const bits = [
    e.at ? new Date(e.at).toLocaleDateString(undefined, { day: "2-digit", month: "short" }) : "—",
    `${e.source_count} ${e.source_count === 1 ? "outlet" : "outlets"}`,
  ];
  if (e.actors.length) bits.push(e.actors.slice(0, 3).join(" · "));
  return bits.join("  ·  ");
}


// The rule people actually get wrong, shown rather than asserted.
//
// "Same topic is not enough" is abstract, and a careful labeller acting in good
// faith still grouped two stories because they shared an ORGANISATION. That is
// not carelessness — it is the intuitive reading, and it is the one thing this
// gold set must not encode, because a shared actor is what the clustering
// already over-weights and what the whole measurement exists to test.
//
// The examples are INVENTED. Using a real pair from the batch would hand the
// answer to whoever meets it later and quietly contaminate that task.
function Guide({ open = false }: { open?: boolean }) {
  return (
    <details
      open={open}
      className="mt-6 border-t pt-5"
      style={{ borderColor: "var(--line)" }}
    >
      <summary className="cursor-pointer text-[14.5px] font-medium" style={{ color: "var(--ink)" }}>
        How to decide
      </summary>
      <div className="mt-4 space-y-5">
        <div className="border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            THE SAME STORY — TICK IT
          </p>
          <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
            &ldquo;Cricketer handed 8-year ban for corruption&rdquo;
          </p>
          <p className="text-[14.5px]" style={{ color: "var(--ink)" }}>
            &ldquo;ICC bans USA player for eight years&rdquo;
          </p>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            One happening, reported twice. Different words, different outlet, same event.
          </p>
        </div>

        <div className="border-l pl-4" style={{ borderColor: "var(--line-strong)" }}>
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            NOT THE SAME STORY — LEAVE IT
          </p>
          <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            &ldquo;State bank signs rural credit deal with farm body&rdquo;
          </p>
          <p className="text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            &ldquo;State bank survey finds rural incomes flat&rdquo;
          </p>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            The same organisation doing two unrelated things. A shared name is not a
            shared story — this is the one most people tick by mistake.
          </p>
        </div>

        <p className="text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
          Ask: <strong style={{ color: "var(--ink)" }}>would one follow the other in a
          single running account of events?</strong> If it is just the same subject,
          the same place or the same person, leave it. Ticking nothing is a real and
          useful answer.
        </p>
      </div>
    </details>
  );
}


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
  claim, position, saving, onAnswer,
}: {
  claim: LabelClaim;
  position: number;
  saving: boolean;
  onAnswer: (verdict: "yes" | "no" | "unsure" | "skip") => void;
}) {
  return (
    <>
      <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-faint)" }}>
        {claim.source} · question {position + 1}
      </p>
      <h1
        className="mt-2 text-[19px] leading-[1.35]"
        style={{ fontFamily: "var(--font-display), serif", textWrap: "pretty" }}
      >
        {claim.title}
      </h1>

      <p className="mt-8 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
        Does this article attribute the highlighted words to{" "}
        <strong style={{ color: "var(--ink)" }}>{claim.speaker}</strong>?
      </p>

      {claim.lead ? (
        <p
          className="mt-4 text-[13.5px] leading-[1.6]"
          style={{ color: "var(--ink-muted)" }}
        >
          <span className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            HOW THE ARTICLE OPENS ·{" "}
          </span>
          {claim.lead}…
        </p>
      ) : null}

      <div
        className="mt-4 border-l-2 pl-4 text-[15px] leading-[1.65]"
        style={{ borderColor: "var(--ink)" }}
      >
        <span style={{ color: "var(--ink-faint)" }}>…{claim.context_before}</span>
        <mark style={{ background: "var(--bg-sunken)", color: "var(--ink)", fontWeight: 500 }}>
          {claim.quote_text}
        </mark>
        <span style={{ color: "var(--ink-faint)" }}>{claim.context_after}…</span>
      </div>

      {claim.article_text ? (
        <details className="mt-4">
          <summary className="cursor-pointer text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            Read the whole article
          </summary>
          <p
            className="mt-3 max-h-[420px] overflow-y-auto whitespace-pre-line text-[14px] leading-[1.7]"
            style={{ color: "var(--ink-muted)" }}
          >
            {claim.article_text}
          </p>
        </details>
      ) : null}

      <div
        className="mt-6 flex flex-wrap items-center gap-3 border-t pt-5"
        style={{ borderColor: "var(--line)" }}
      >
        <button
          type="button" disabled={saving} onClick={() => onAnswer("yes")}
          className="h-11 rounded-full px-5 text-[14.5px] font-medium disabled:opacity-50"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Yes — {claim.speaker.slice(0, 24)} said it
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("no")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
        >
          No — someone else, or nobody
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("unsure")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
        >
          Not sure
        </button>
        <button
          type="button" disabled={saving} onClick={() => onAnswer("skip")}
          className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
          style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}
        >
          Can&apos;t read this
        </button>
      </div>

      {/* Open on the FIRST question only. A claims labeller arrives with an
          invite token, which skips the landing screen where the story flow
          shows its guide open — so collapsed here meant the guide was never put
          in front of anyone. The point of it is being read BEFORE the first
          judgement, not after a wrong one. */}
      <ClaimGuide open={position === 0} />
    </>
  );
}



/** Shown BEFORE the first task, and dismissed deliberately.
 *
 *  The first round shipped its guidance as a collapsed <details> and 30% of the
 *  123 tasks came back with the two labellers disagreeing — not randomly, but
 *  with opposite systematic biases. One ticked on any shared word (a "Monsoon
 *  Marathon" grouped with a parliamentary "Monsoon Session"); the other missed
 *  the same cricket ban reported in English and in Kannada. Neither had read the
 *  guidance, because nothing made them.
 *
 *  Every example below is a REAL disagreement from that round, which is why they
 *  are worth the screen space: they are the mistakes these two people actually
 *  make, not invented ones.
 */
/** The same-happening task: stricter than the story task. One incident, any
 *  language, any wording — but the follow-up is a different happening here. */
function EventPrimer({ onStart }: { onStart: () => void }) {
  return (
    <div className="mx-auto max-w-[640px] pt-2">
      <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        READ THIS FIRST · ABOUT TWO MINUTES
      </p>
      <h1 className="mt-2 text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Is this the same happening?
      </h1>
      <p className="mt-4 text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
        You will see one report — usually in Hindi, Kannada or another language, with our English
        headline above it — then English reports from the same days. Tick the ones that report the
        <strong> same incident</strong>: the same thing, the same people, the same day. Wording and
        language do not matter. This is narrower than &ldquo;the same story&rdquo;.
      </p>
      <div className="mt-7 border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO</p>
        <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
          <li>Tick every English report of <strong>the one incident</strong>, however it is worded.</li>
          <li>Read the outlet&apos;s own headline under ours when they seem to disagree; the outlet&apos;s is the truth.</li>
          <li>Tick nothing when nothing matches — that is the most common right answer here.</li>
          <li>Answer <strong>Not sure</strong> when you cannot tell from the headlines. It is a real answer.</li>
        </ul>
      </div>
      <div className="mt-6 border-l-2 pl-4" style={{ borderColor: "var(--danger, #b91c1c)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO NOT</p>
        <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
          <li>Do not tick the <strong>follow-up</strong>. The arrests the day after the attack are a different happening in this task (they were the same <em>story</em> in the other one).</li>
          <li>Do not tick a <strong>different incident of the same kind</strong>: two foundation stones laid in two towns, two Lokayukta arrests, two road crashes.</li>
          <li>Do not tick because the two share a name, a place, or a subject.</li>
        </ul>
      </div>
      <p className="mt-7 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        EXAMPLES FROM THE DATA THIS ROUND CAME FROM
      </p>
      <div className="mt-3 space-y-4">
        {[
          ["TICK — “India rejects China-Pakistan Boundary Joint Commission” (Aaj Tak, Hindi) with “India rejects Pakistan-China Boundary Joint Commission” (The Hindu)",
           "One statement by the MEA, reported in two languages. The order of the country names is the only difference."],
          ["TICK — a Kannada report that Anant Nag will receive the Dadasaheb Phalke Award, with the English reports of the same announcement",
           "Same award, same day, same actor. The words share nothing because the scripts share nothing."],
          ["DO NOT TICK — “Foundation stone laid for Bidar Fort development” with “Foundation stone laid for Mahadeshwara Swamy temple”",
           "Same kind of thing happening in two places. Two incidents."],
          ["DO NOT TICK — “Jarange ends 20-day fast” with “Jarange dehydrated, doctors warn”, if they are a day apart",
           "Same man, same story, two happenings. In this task that is a No."],
        ].map(([head, body]) => (
          <div key={head}>
            <p className="text-[14px] font-medium" style={{ color: "var(--ink)" }}>{head}</p>
            <p className="mt-1 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>{body}</p>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={onStart}
        className="mt-8 h-11 rounded-full px-6 text-[14.5px] font-medium"
        style={{ background: "var(--ink)", color: "var(--bg)" }}
      >
        Start
      </button>
    </div>
  );
}

function Primer({ kind, onStart }: { kind: string; onStart: () => void }) {
  const claim = kind === "claim_attribution";
  if (kind === "event_identity") return <EventPrimer onStart={onStart} />;
  return (
    <div className="mx-auto max-w-[640px] pt-2">
      <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        READ THIS FIRST · ABOUT TWO MINUTES
      </p>
      <h1 className="mt-2 text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        {claim ? "Did this article put these words in this person's mouth?" : "Is this the same story?"}
      </h1>

      <p className="mt-4 text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
        {claim
          ? "We check automatically that the quote is copied correctly. What a machine cannot check is whether the article credits it to the right person. That is the only thing you are judging."
          : "You will see one headline, then others from around the same time. Tick the ones covering the same unfolding story. The test is whether it is the same real-world happening — not whether the headlines look alike."}
      </p>

      <div className="mt-7 border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO</p>
        {claim ? (
          <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
            <li>Read the words either side of the quote — that is usually where the answer is.</li>
            <li>Open “Read the whole article” when the text near the quote only says “he” or “the Collector”.</li>
            <li>Answer <strong>Not sure</strong> when you genuinely cannot tell. It is a real answer.</li>
          </ul>
        ) : (
          <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
            <li>
              Tick <strong>every outlet covering the one incident</strong> — five reports of one
              breach are five ticks, not none.
            </li>
            <li>
              Tick when the words share nothing, <strong>including across languages</strong>. A
              Kannada and a Hindi report of one final are one story.
            </li>
            <li>Tick the direct follow-up: the arrests after the attack are the same story.</li>
            <li>Ask: would one follow the other in a single running account of one event?</li>
            <li>Tick nothing when nothing matches. That is a real and useful answer.</li>
          </ul>
        )}
      </div>

      <div className="mt-6 border-l-2 pl-4" style={{ borderColor: "var(--danger, #b91c1c)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO NOT</p>
        {claim ? (
          <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            <li>Do not judge whether the claim is <em>true</em>, fair, or well argued.</li>
            <li>Do not answer Yes because the quote sounds like something that person would say.</li>
            <li>Do not guess when the article never names who spoke — that is a No or a Not sure.</li>
          </ul>
        ) : (
          <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            <li>Do not tick because two headlines share a <strong>word</strong>.</li>
            <li>Do not tick because they share an <strong>organisation</strong>, a person, or a place.</li>
            <li>Do not tick because they share a <strong>subject</strong>. Two dengue stories are two stories.</li>
          </ul>
        )}
      </div>

      <p className="mt-7 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        REAL MISTAKES FROM THE LAST ROUND
      </p>
      <div className="mt-3 space-y-4">
        {(claim
          ? [
              ["NO — right quote, wrong mouth",
               "The quotation is copied perfectly from the article, but the words either side credit it to somebody else. This is the one no automatic check can catch."],
              ["NOT SURE — the article only says “the Collector”",
               "If you cannot tie that role to the person named in the question, even after opening the full article, say Not sure rather than guessing."],
            ]
          : [
              ["WRONG — “Nandi Hills Monsoon Marathon” ticked with “tribunal reforms Bill in Monsoon Session”",
               "These share the word “Monsoon” and nothing else. A shared word is not a shared story."],
              ["WRONG — “CFTRI and NABARD join hands” ticked with “NABARD survey on rural incomes”",
               "Same organisation, two unrelated things it did. A shared organisation is not a shared story."],
              ["MISSED — the Hugging Face breach, five outlets, none ticked",
               "“Hugging Face Breached by Autonomous AI Agent” and “OpenAI Says Its Models Accidentally Hacked Hugging Face” are one breach reported twice. All five belonged together."],
              ["MISSED — “Supreme Court declines urgent listing” not ticked with “‘Don’t waste our time’: CJI declines urgent listing”",
               "One court hearing, two headlines that share almost no words. Different wording is the normal case, not a reason to separate."],
              ["MISSED — the Anantnag attack not ticked with “Policeman killed in terror attack in Anantnag”",
               "Same attack. “Over 2,000 Detained After Cop Killed In Anantnag” is the direct follow-up and belongs with it too."],
              ["MISSED — the Kannada CWG javelin report not ticked with the Hindi one",
               "Same three athletes, same final, two languages. These matter more than any other kind and are the easiest to miss, because the words share nothing."],
            ]
        ).map(([head, body]) => (
          <div key={head}>
            <p className="text-[14px] font-medium" style={{ color: "var(--ink)" }}>{head}</p>
            <p className="mt-1 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>{body}</p>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onStart}
        className="mt-8 h-11 rounded-full px-6 text-[14.5px] font-medium"
        style={{ background: "var(--ink)", color: "var(--bg)" }}
      >
        I have read this — start
      </button>
      <p className="mt-3 text-[13px]" style={{ color: "var(--ink-faint)" }}>
        You can stop whenever you like; it remembers where you got to.
      </p>
    </div>
  );
}

/** What "attributed" means, shown rather than asserted — the same lesson the
 *  story guide had to learn when a careful labeller grouped by shared
 *  organisation in good faith. */
function ClaimGuide({ open = false }: { open?: boolean }) {
  return (
    <details open={open} className="mt-8 border-t pt-5" style={{ borderColor: "var(--line)" }}>
      <summary className="cursor-pointer text-[14.5px] font-medium" style={{ color: "var(--ink)" }}>
        How to decide
      </summary>
      <div className="mt-4 space-y-5">
        <div className="border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            YES — THE ARTICLE SAYS SO
          </p>
          <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
            …the minister said the state would{" "}
            <mark style={{ background: "var(--bg-sunken)" }}>double its outlay</mark>…
          </p>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            Asked about <strong>the minister</strong> — the words either side name the
            speaker. That is the whole test.
          </p>
        </div>

        <div className="border-l pl-4" style={{ borderColor: "var(--line-strong)" }}>
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            NO — RIGHT QUOTE, WRONG MOUTH
          </p>
          <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            …opposition leaders called it{" "}
            <mark style={{ background: "var(--bg-sunken)" }}>optimistic at best</mark>…
          </p>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            Asked about <strong>the minister</strong>. The quotation is real and
            copied correctly — somebody else said it. This is the mistake worth
            catching, and it is invisible to every automatic check we have.
          </p>
        </div>

        <p className="text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
          You are not judging whether the claim is TRUE, or fair, or well argued —
          only whether this article puts these words in this person&apos;s mouth. If
          the surrounding text does not say who spoke, that is a{" "}
          <strong style={{ color: "var(--ink)" }}>No</strong>, not a guess.
        </p>
      </div>
    </details>
  );
}

export default function LabelPage({ params }: { params: Promise<{ key: string }> }) {
  const [batchKey, setBatchKey] = useState("");
  const [who, setWho] = useState("");
  const [token, setToken] = useState("");
  const [draftWho, setDraftWho] = useState("");
  const [joinError, setJoinError] = useState("");
  const [batch, setBatch] = useState<LabelBatch | null>(null);
  // The same-happening task (article -> event) is narrower than the story task:
  // the copy on screen says so at every step.
  const sameEvent = batch?.kind === "event_identity";
  // Null until read from storage, so the first paint does not flash the primer at
  // someone who has already dismissed it.
  const [primed, setPrimed] = useState<boolean | null>(null);
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
    async (unsure: boolean, skipped = false, agreed = false) => {
      if (!task || saving) return;
      setSaving(true);
      try {
        await postLabelAnswer(batchKey, {
          task_id: task.id,
          token,
          // A skip carries no opinion, so whatever was ticked is discarded rather
          // than filed as a judgement nobody meant to give.
          // A claim answer has no candidate ids. "The article does attribute this
          // quote to this speaker" is carried as a single sentinel selection, so
          // the same responses table and the same agreement maths serve both kinds.
          selected: skipped ? [] : task.claim ? (agreed ? [task.id] : []) : [...picked],
          unsure,
          skipped,
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
      if (Number.isInteger(n) && n >= 1 && n <= (task.candidates?.length ?? 0)) {
        ev.preventDefault();
        toggle((task.candidates ?? [])[n - 1].id);
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
        <p className="mt-4 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
          YOUR NAME IS ONLY USED TO REMEMBER WHERE YOU GOT TO
        </p>
        <Guide open />
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

      {state === "ready" && task && primed === false && (
        <Primer
          kind={batch?.kind ?? "story_boundary"}
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

      {state === "ready" && task && primed !== false && (
        task.claim ? (
          <ClaimTask
            claim={task.claim}
            position={task.position}
            saving={saving}
            onAnswer={(verdict) => void submit(verdict === "unsure", verdict === "skip",
                                              verdict === "yes")}
          />
        ) : (
        <>
          <p className="font-mono text-[11px] uppercase" style={{ color: "var(--ink-faint)" }}>
            {task.sector ?? "news"} · question {task.position + 1}
          </p>
          <h1
            className="mt-2 text-[23px] leading-[1.3]"
            style={{ fontFamily: "var(--font-display), serif", textWrap: "pretty" }}
          >
            {task.seed?.title}
          </h1>
          {sameEvent && task.seed?.native_title && task.seed.native_title !== task.seed.title && (
            <p className="mt-2 text-[15px] leading-[1.5]" style={{ color: "var(--ink)" }} lang={task.seed.language || undefined}>
              {task.seed.native_title}
            </p>
          )}
          <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            {task.seed ? provenance(task.seed) : ""}
          </p>

          <p className="mt-8 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            {sameEvent ? "Which of these report the same happening — the same incident, the same day?" : "Which of these are part of the same unfolding story?"}
          </p>

          <ul className="mt-3">
            {(task.candidates ?? []).map((c, i) => {
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
                        className="mt-1 block font-mono text-[11px]"
                        style={{ color: "var(--ink-faint)" }}
                      >
                        {provenance(c)}
                        {/* Provenance, never a score: a number on the line would
                            anchor the judgement this set exists to collect. */}
                        {c.signals.length ? `  ·  ${c.signals.map((x) => x.split(":")[0]).join("+")}` : ""}
                      </span>
                    </span>
                    <span
                      aria-hidden
                      className="ml-auto shrink-0 font-mono text-[11px]"
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
            {/* Distinct from "Not sure" on purpose. "Not sure" says the STORY is
                ambiguous and is read as a signal about the boundary; this says the
                READER cannot assess it, and routes the task to someone else. 72 of
                this batch's 123 tasks carry a Kannada, Devanagari or Tamil
                headline, so without it the only exits were to guess or to mislabel
                a language barrier as ambiguity. */}
            <button
              type="button"
              disabled={saving}
              onClick={() => void submit(false, true)}
              className="h-11 rounded-full border px-5 text-[14.5px] disabled:opacity-50"
              style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}
            >
              Can&apos;t read this
            </button>
            <span className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
              KEYS 1–{(task.candidates?.length ?? 0)} TOGGLE · ENTER SUBMITS
            </span>
          </div>

          <p className="mt-6 text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            {sameEvent ? (
              <>The follow-up is a different happening here; a different incident of the same kind is too. <strong>Not sure</strong> is a real answer.</>
            ) : (
              <>Same topic isn&apos;t enough — two different court cases about one law are two
              stories. <strong>Not sure</strong> is a real answer; it keeps genuinely hard
              calls out of the training data rather than guessing at them.</>
            )}
          </p>

          {/* An INVITED labeller never sees the join screen, so this is the only
              route the worked example has to them. Collapsed, because it is
              reference rather than instruction once you are going. */}
          <Guide />
        </>
        )
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
