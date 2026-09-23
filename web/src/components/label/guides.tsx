"use client";

/**
 * The guides for each kind of labelling task — what it asks, DO / DO NOT, and
 * worked examples. Moved out of the task page (web/src/app/label/[key]) so the
 * same words can teach on /label/learn/<kind> before anyone opens a batch, and
 * so the task page stops being a 1,000-line file (plan: labeller workspace,
 * phase 2).
 *
 * The examples keep their two rules from the task page: story and claim
 * examples are INVENTED, because a real pair from a batch would hand its answer
 * to whoever meets it later; the same-happening examples are REAL disagreements
 * from the first round, because they are the mistakes people actually make.
 */

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
export function Guide({ open = false }: { open?: boolean }) {
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


/** The third judgement is intentionally asked only about pairs already agreed
 *  NOT to be the same story. It separates useful context from retrieval noise;
 *  it must not quietly teach the story boundary again. */
export function TopicGuide({ open = false }: { open?: boolean }) {
  return (
    <details open={open} className="mt-6 border-t pt-5" style={{ borderColor: "var(--line)" }}>
      <summary className="cursor-pointer text-[14.5px] font-medium" style={{ color: "var(--ink)" }}>
        How to decide
      </summary>
      <div className="mt-4 space-y-5">
        <div className="border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            RELATED CONTEXT — TICK IT
          </p>
          <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
            &ldquo;Court pauses new coastal zoning rules&rdquo;
          </p>
          <p className="text-[14.5px]" style={{ color: "var(--ink)" }}>
            &ldquo;Fishing groups challenge the same coastal policy&rdquo;
          </p>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            Different proceedings, but one policy issue. A reader of either would
            reasonably want the other under related context.
          </p>
        </div>
        <div className="border-l pl-4" style={{ borderColor: "var(--line-strong)" }}>
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
            RETRIEVAL NOISE — LEAVE IT
          </p>
          <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            &ldquo;State bank signs rural credit agreement&rdquo;
          </p>
          <p className="text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
            &ldquo;State bank appoints a new technology chief&rdquo;
          </p>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
            The organisation is shared, but the subject is not. Same person, place,
            organisation, country, or broad sector is not enough by itself.
          </p>
        </div>
        <p className="text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
          These pairs have already been judged as different stories. Ask only:
          <strong style={{ color: "var(--ink)" }}> would this be genuinely useful
          context beside the first headline?</strong>
        </p>
      </div>
    </details>
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
 *  language, any wording, any day it was reported — but the follow-up is a
 *  different happening here.
 *
 *  "Any day" is the founder's correction (2026-09-23): this said "the same day",
 *  and the cross-language batch shows 252 of its 364 candidates on another day
 *  than their seed, up to five days apart. Every late report of the same
 *  incident would have been answered No. What separates two happenings is that
 *  something NEW happened, never the date an outlet got round to it. */
export function EventPrimer({ onStart, action = "Start" }: { onStart: () => void; action?: string }) {
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
        headline above it — then English reports from the days around it. Tick the ones that report
        the <strong>same incident</strong>: the same thing that happened, to the same people.
        <strong> When it was reported does not matter</strong> — an outlet that got to it a day or
        three later is still reporting the same happening. Neither do wording and language. This is
        narrower than &ldquo;the same story&rdquo;.
      </p>
      <div className="mt-7 border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO</p>
        <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
          <li>Tick every English report of <strong>the one incident</strong>, however it is worded.</li>
          <li>Tick a <strong>late report</strong> of it too. Outlets report on their own clock; the date under a headline says when they wrote, not what happened.</li>
          <li>Read the outlet&apos;s own headline under ours when they seem to disagree; the outlet&apos;s is the truth.</li>
          <li>Tick nothing when nothing matches — that is the most common right answer here.</li>
          <li>Answer <strong>Not sure</strong> when you cannot tell from the headlines. It is a real answer.</li>
        </ul>
      </div>
      <div className="mt-6 border-l-2 pl-4" style={{ borderColor: "var(--danger, #b91c1c)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO NOT</p>
        <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
          <li>Do not tick the <strong>follow-up</strong>: something new that happened after the incident. The arrests the day after the attack are a different happening in this task (they were the same <em>story</em> in the other one). The test is whether something new happened, never the date on the report.</li>
          <li>Do not tick a <strong>different incident of the same kind</strong>: two foundation stones laid in two towns, two Lokayukta arrests, two road crashes.</li>
          <li>Do not tick because the two share a name, a place, or a subject.</li>
        </ul>
      </div>
      <p className="mt-7 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        EXAMPLES — FROM THE DATA THIS ROUND CAME FROM, UNLESS MARKED
      </p>
      <div className="mt-3 space-y-4">
        {[
          ["TICK — “India rejects China-Pakistan Boundary Joint Commission” (Aaj Tak, Hindi) with “India rejects Pakistan-China Boundary Joint Commission” (The Hindu)",
           "One statement by the MEA, reported in two languages. The order of the country names is the only difference."],
          ["TICK — a Kannada report that Anant Nag will receive the Dadasaheb Phalke Award, with the English reports of the same announcement",
           "Same award, same announcement, same actor. The words share nothing because the scripts share nothing."],
          ["DO NOT TICK — “Foundation stone laid for Bidar Fort development” with “Foundation stone laid for Mahadeshwara Swamy temple”",
           "Same kind of thing happening in two places. Two incidents."],
          ["DO NOT TICK — “Jarange ends 20-day fast” with “Jarange dehydrated, doctors warn”",
           "Same man, same story, two things that happened: the fast ended, then his health failed. A No because something new happened — not because of the dates."],
          ["TICK — a Kannada report of a bridge collapse dated the 12th, with an English report of the same collapse dated the 13th",
           "One collapse. The English outlet reported it a day later: a late report, not a different happening.",
           "ILLUSTRATION"],
        ].map(([head, body, note]) => (
          <div key={head}>
            {note && <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>{note}</p>}
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
        {action}
      </button>
    </div>
  );
}

/** `action` labels the button: on a batch it starts the work; on /label/learn it
 *  goes wherever the reader goes next. */
export function Primer({ kind, onStart, action, children }: { kind: string; onStart: () => void; action?: string; children?: React.ReactNode }) {
  const claim = kind === "claim_attribution";
  if (kind === "event_identity") return <EventPrimer onStart={onStart} action={action} />;
  if (kind === "quote_rendering") return <RenderingPrimer onStart={onStart} action={action} />;
  if (kind === "topic_relation") {
    return (
      <div className="mx-auto max-w-[640px] pt-2">
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
          READ THIS FIRST · ABOUT ONE MINUTE
        </p>
        <h1 className="mt-2 text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          Is this useful related context?
        </h1>
        <p className="mt-4 text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
          Both reviewers already agreed these are <strong>different stories</strong>.
          Now tick only the headlines that concern the same issue closely enough to
          help a reader understand the first one.
        </p>
        <TopicGuide open />
        <button
          type="button"
          onClick={onStart}
          className="mt-8 h-11 rounded-full px-6 text-[14.5px] font-medium"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {action ?? "I have read this — start"}
        </button>
        <p className="mt-3 text-[13px]" style={{ color: "var(--ink-faint)" }}>
          You can stop whenever you like; it remembers where you got to.
        </p>
      </div>
    );
  }
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
      {children}

      <button
        type="button"
        onClick={onStart}
        className="mt-8 h-11 rounded-full px-6 text-[14.5px] font-medium"
        style={{ background: "var(--ink)", color: "var(--bg)" }}
      >
        {action ?? "I have read this — start"}
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
export function ClaimGuide({ open = false }: { open?: boolean }) {
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


/** The quote-rendering task: same statement in two languages, or was it
 *  spoken in the language printed? The examples are INVENTED, for the reason
 *  the story guide gives — a real pair from the batch would hand out its answer.
 *
 *  The case to teach is the one the shadow run showed is hard: the model
 *  flagged half of Telugu quotes as translations. Sometimes that is right (a
 *  Telugu outlet quoting the Prime Minister's Hindi speech), sometimes wrong
 *  (a Telugu minister speaking to Telugu reporters). Only the occasion decides. */
export function RenderingPrimer({ onStart, action = "I have read this — start" }: { onStart: () => void; action?: string }) {
  return (
    <div className="mx-auto max-w-[640px] pt-2">
      <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>READ THIS FIRST · ABOUT TWO MINUTES</p>
      <h1 className="mt-2 text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Same statement, or a translation?
      </h1>
      <p className="mt-4 text-[15px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
        Prism checks that every quote is copied exactly from its article. What it cannot check is whether the article
        printed the words the person <strong>spoke</strong>, or its own translation of them. You answer one of two questions:
        whether two quotes in two languages are the same statement, or whether a quote was spoken in the language it is
        printed in.
      </p>
      <div className="mt-7 border-l-2 pl-4" style={{ borderColor: "var(--ink)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO</p>
        <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink)" }}>
          <li>Say <strong>same</strong> when both quotes report the same thing said, even though a translation never reads word for word.</li>
          <li>Say <strong>translated</strong> when a person is quoted in a language they were not speaking: a prime minister&apos;s Hindi speech printed in Kannada, a foreign leader printed in Tamil.</li>
          <li>Say <strong>spoken so</strong> when the occasion fits: a state minister talking to reporters in the state&apos;s language.</li>
          <li>Answer <strong>Not sure</strong> when the article does not tell you where or to whom it was said. It is a real answer.</li>
        </ul>
      </div>
      <div className="mt-6 border-l-2 pl-4" style={{ borderColor: "var(--danger, #b91c1c)" }}>
        <p className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>DO NOT</p>
        <ul className="mt-2 space-y-2 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
          <li>Do not say <strong>same</strong> because two quotes are on the same subject. Two things one person said about one policy are two statements.</li>
          <li>Do not guess the language from the outlet alone. A Telugu paper quoting a Telugu minister prints the minister&apos;s own words; the same paper quoting the Prime Minister translates them.</li>
          <li>Do not judge whether the statement is true, fair or well said.</li>
        </ul>
      </div>
      <p className="mt-7 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>WORKED EXAMPLES · INVENTED</p>
      <div className="mt-3 space-y-4">
        {[
          ["SAME — an English report and a Kannada report of a foreign leader’s speech",
           "Both carry the one thing she said. Neither is in the language she spoke; both are translations of it — and they are still the same statement."],
          ["TRANSLATED — a national leader’s Hindi speech, quoted in a Telugu paper",
           "The speech was given in Hindi. The Telugu words are the paper’s own translation."],
          ["SPOKEN SO — a Kannada minister, quoted in Kannada after a Bengaluru press meet",
           "The occasion is a Kannada press meet; the quote is the minister’s own words."],
          ["NOT SURE — a bilingual politician, quoted in English, with no hint of the occasion",
           "Nothing in the article says which language was used. Guessing is worse than saying so."],
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
        {action}
      </button>
    </div>
  );
}
