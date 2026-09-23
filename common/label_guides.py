"""The labelling guides — what each task asks, DO / DO NOT, and worked examples —
served only to the people who label (plan: guides behind sign-in, phase B).

WHY THIS IS SERVER DATA. The guides lived in web/src/components/label/guides.tsx,
which ships in the site's public JavaScript: hiding the page behind sign-in
would have stopped a casual visitor and not a determined one (founder,
2026-09-23: "do not leak this to outsiders"). They are now sent by
api/routes/labeller.py to an account that has applied, and by api/routes/label.py
to a valid invite for a batch of that kind — never to anyone else. CI checks
that no guide sentence is in the built site (web/scripts/check-no-guides.mjs).

The words moved over unchanged. Inline markup is the smallest that covers
them: **strong**, *emphasis*, ==highlight== (the quote inside its sentence).

The examples keep their two rules: story, topic, claim and rendering examples
are INVENTED, because a real pair from a batch would hand its answer to whoever
meets it later; the same-happening examples are REAL disagreements from the
first round (one is marked ILLUSTRATION), because they are the mistakes people
actually make.

`mark` on an example picks its icon: "yes" (Check) for what should be ticked or
said, "no" (Dash) for what should not; absent when neither fits. The verdict is
always also a word in `head` — the Legend Rule, never an icon alone.
"""

from __future__ import annotations

from typing import Any

START = "I have read this — start"
STOP_ANY_TIME = "You can stop whenever you like; it remembers where you got to."

GUIDES: dict[str, dict[str, Any]] = {
    "story_boundary": {
        "question": "Is this the same story?",
        "minutes": 2,
        "in_short": "Tick every report of the one unfolding story — however it is worded, in any language — and "
                    "never for a shared word, name or subject.",
        "lede": ["You will see one headline, then others from around the same time. Tick the ones covering the "
                 "same unfolding story. The test is whether it is the same real-world happening — not whether "
                 "the headlines look alike."],
        "do": [
            "Tick **every outlet covering the one incident** — five reports of one breach are five ticks, not none.",
            "Tick when the words share nothing, **including across languages**. A Kannada and a Hindi report of "
            "one final are one story.",
            "Tick the direct follow-up: the arrests after the attack are the same story.",
            "Ask: would one follow the other in a single running account of one event?",
            "Tick nothing when nothing matches. That is a real and useful answer.",
        ],
        "dont": [
            "Do not tick because two headlines share a **word**.",
            "Do not tick because they share an **organisation**, a person, or a place.",
            "Do not tick because they share a **subject**. Two dengue stories are two stories.",
        ],
        "examples_label": "Real mistakes from the last round",
        "examples": [
            {"mark": "no", "head": "WRONG — “Nandi Hills Monsoon Marathon” ticked with “tribunal reforms Bill in Monsoon Session”",
             "body": "These share the word “Monsoon” and nothing else. A shared word is not a shared story."},
            {"mark": "no", "head": "WRONG — “CFTRI and NABARD join hands” ticked with “NABARD survey on rural incomes”",
             "body": "Same organisation, two unrelated things it did. A shared organisation is not a shared story."},
            {"mark": "yes", "head": "MISSED — the Hugging Face breach, five outlets, none ticked",
             "body": "“Hugging Face Breached by Autonomous AI Agent” and “OpenAI Says Its Models Accidentally Hacked "
                     "Hugging Face” are one breach reported twice. All five belonged together."},
            {"mark": "yes", "head": "MISSED — “Supreme Court declines urgent listing” not ticked with “‘Don’t waste our "
                                    "time’: CJI declines urgent listing”",
             "body": "One court hearing, two headlines that share almost no words. Different wording is the normal "
                     "case, not a reason to separate."},
            {"mark": "yes", "head": "MISSED — the Anantnag attack not ticked with “Policeman killed in terror attack in Anantnag”",
             "body": "Same attack. “Over 2,000 Detained After Cop Killed In Anantnag” is the direct follow-up and "
                     "belongs with it too."},
            {"mark": "yes", "head": "MISSED — the Kannada CWG javelin report not ticked with the Hindi one",
             "body": "Same three athletes, same final, two languages. These matter more than any other kind and are "
                     "the easiest to miss, because the words share nothing."},
        ],
        # The rule people actually get wrong, shown rather than asserted: a
        # careful labeller grouped two stories because they shared an
        # ORGANISATION — the intuitive reading, and the one thing this gold set
        # must not encode. INVENTED, so no batch pair's answer leaks.
        "decide": {
            "blocks": [
                {"mark": "yes", "label": "The same story — tick it",
                 "lines": ["“Cricketer handed 8-year ban for corruption”", "“ICC bans USA player for eight years”"],
                 "body": "One happening, reported twice. Different words, different outlet, same event."},
                {"mark": "no", "label": "Not the same story — leave it",
                 "lines": ["“State bank signs rural credit deal with farm body”", "“State bank survey finds rural incomes flat”"],
                 "body": "The same organisation doing two unrelated things. A shared name is not a shared story — "
                         "this is the one most people tick by mistake."},
            ],
            "closing": "Ask: **would one follow the other in a single running account of events?** If it is just the "
                       "same subject, the same place or the same person, leave it. Ticking nothing is a real and "
                       "useful answer.",
        },
        "start": START,
        "after": STOP_ANY_TIME,
    },
    "event_identity": {
        "question": "Is this the same happening?",
        "minutes": 2,
        "in_short": "Tick every report of the one incident, whatever day an outlet reported it; never the follow-up, "
                    "and never a different incident of the same kind.",
        "lede": ["You will see one report — usually in Hindi, Kannada or another language, with our English headline "
                 "above it — then English reports from the days around it. Tick the ones that report the **same "
                 "incident**: the same thing that happened, to the same people. **When it was reported does not "
                 "matter** — an outlet that got to it a day or three later is still reporting the same happening. "
                 "Neither do wording and language. This is narrower than “the same story”."],
        "do": [
            "Tick every English report of **the one incident**, however it is worded.",
            "Tick a **late report** of it too. Outlets report on their own clock; the date under a headline says when "
            "they wrote, not what happened.",
            "Read the outlet's own headline under ours when they seem to disagree; the outlet's is the truth.",
            "Tick nothing when nothing matches — that is the most common right answer here.",
            "Answer **Not sure** when you cannot tell from the headlines. It is a real answer.",
        ],
        "dont": [
            "Do not tick the **follow-up**: something new that happened after the incident. The arrests the day after "
            "the attack are a different happening in this task (they were the same *story* in the other one). The "
            "test is whether something new happened, never the date on the report.",
            "Do not tick a **different incident of the same kind**: two foundation stones laid in two towns, two "
            "Lokayukta arrests, two road crashes.",
            "Do not tick because the two share a name, a place, or a subject.",
        ],
        "examples_label": "Examples — from the data this round came from, unless marked",
        "examples": [
            {"mark": "yes", "head": "TICK — “India rejects China-Pakistan Boundary Joint Commission” (Aaj Tak, Hindi) with "
                                    "“India rejects Pakistan-China Boundary Joint Commission” (The Hindu)",
             "body": "One statement by the MEA, reported in two languages. The order of the country names is the only "
                     "difference."},
            {"mark": "yes", "head": "TICK — a Kannada report that Anant Nag will receive the Dadasaheb Phalke Award, with "
                                    "the English reports of the same announcement",
             "body": "Same award, same announcement, same actor. The words share nothing because the scripts share "
                     "nothing."},
            {"mark": "no", "head": "DO NOT TICK — “Foundation stone laid for Bidar Fort development” with “Foundation "
                                   "stone laid for Mahadeshwara Swamy temple”",
             "body": "Same kind of thing happening in two places. Two incidents."},
            {"mark": "no", "head": "DO NOT TICK — “Jarange ends 20-day fast” with “Jarange dehydrated, doctors warn”",
             "body": "Same man, same story, two things that happened: the fast ended, then his health failed. A No "
                     "because something new happened — not because of the dates."},
            {"mark": "yes", "illustration": True,
             "head": "TICK — a Kannada report of a bridge collapse dated the 12th, with an English report of the same "
                     "collapse dated the 13th",
             "body": "One collapse. The English outlet reported it a day later: a late report, not a different "
                     "happening."},
        ],
        "start": "Start",
        "after": None,
    },
    "topic_relation": {
        "question": "Is this useful related context?",
        "minutes": 1,
        "in_short": "These are already different stories; tick only what would genuinely help a reader of the first "
                    "headline.",
        "lede": ["Both reviewers already agreed these are **different stories**. Now tick only the headlines that "
                 "concern the same issue closely enough to help a reader understand the first one."],
        "do": [],
        "dont": [],
        "examples_label": None,
        "examples": [],
        # Asked only about pairs already agreed NOT to be the same story: it
        # separates useful context from retrieval noise and must not quietly
        # teach the story boundary again. INVENTED.
        "decide": {
            "blocks": [
                {"mark": "yes", "label": "Related context — tick it",
                 "lines": ["“Court pauses new coastal zoning rules”", "“Fishing groups challenge the same coastal policy”"],
                 "body": "Different proceedings, but one policy issue. A reader of either would reasonably want the "
                         "other under related context."},
                {"mark": "no", "label": "Retrieval noise — leave it",
                 "lines": ["“State bank signs rural credit agreement”", "“State bank appoints a new technology chief”"],
                 "body": "The organisation is shared, but the subject is not. Same person, place, organisation, "
                         "country, or broad sector is not enough by itself."},
            ],
            "closing": "These pairs have already been judged as different stories. Ask only: **would this be genuinely "
                       "useful context beside the first headline?**",
        },
        "start": START,
        "after": STOP_ANY_TIME,
    },
    "claim_attribution": {
        "question": "Did this article put these words in this person's mouth?",
        "minutes": 2,
        "in_short": "Judge only whether the article credits these words to this person — never whether they are true.",
        "lede": ["We check automatically that the quote is copied correctly. What a machine cannot check is whether "
                 "the article credits it to the right person. That is the only thing you are judging."],
        "do": [
            "Read the words either side of the quote — that is usually where the answer is.",
            "Open “Read the whole article” when the text near the quote only says “he” or “the Collector”.",
            "Answer **Not sure** when you genuinely cannot tell. It is a real answer.",
        ],
        "dont": [
            "Do not judge whether the claim is *true*, fair, or well argued.",
            "Do not answer Yes because the quote sounds like something that person would say.",
            "Do not guess when the article never names who spoke — that is a No or a Not sure.",
        ],
        "examples_label": "Real mistakes from the last round",
        "examples": [
            {"mark": "no", "head": "NO — right quote, wrong mouth",
             "body": "The quotation is copied perfectly from the article, but the words either side credit it to "
                     "somebody else. This is the one no automatic check can catch."},
            {"head": "NOT SURE — the article only says “the Collector”",
             "body": "If you cannot tie that role to the person named in the question, even after opening the full "
                     "article, say Not sure rather than guessing."},
        ],
        # What "attributed" means, shown rather than asserted. INVENTED.
        "decide": {
            "blocks": [
                {"mark": "yes", "label": "Yes — the article says so",
                 "lines": ["…the minister said the state would ==double its outlay==…"],
                 "body": "Asked about **the minister** — the words either side name the speaker. That is the whole test."},
                {"mark": "no", "label": "No — right quote, wrong mouth",
                 "lines": ["…opposition leaders called it ==optimistic at best==…"],
                 "body": "Asked about **the minister**. The quotation is real and copied correctly — somebody else said "
                         "it. This is the mistake worth catching, and it is invisible to every automatic check we have."},
            ],
            "closing": "You are not judging whether the claim is TRUE, or fair, or well argued — only whether this "
                       "article puts these words in this person's mouth. If the surrounding text does not say who "
                       "spoke, that is a **No**, not a guess.",
        },
        "start": START,
        "after": STOP_ANY_TIME,
    },
    # The case to teach is the one the shadow run showed is hard: the model
    # flagged half of Telugu quotes as translations. Sometimes that is right (a
    # Telugu outlet quoting the Prime Minister's Hindi speech), sometimes wrong
    # (a Telugu minister speaking to Telugu reporters). Only the occasion decides.
    "quote_rendering": {
        "question": "Same statement, or a translation?",
        "minutes": 2,
        "in_short": "Say whether two quotes are one statement, or whether a quote is in the language it was spoken — "
                    "from the occasion, never the outlet alone.",
        "lede": ["Prism checks that every quote is copied exactly from its article. What it cannot check is whether "
                 "the article printed the words the person **spoke**, or its own translation of them. You answer one "
                 "of two questions: whether two quotes in two languages are the same statement, or whether a quote "
                 "was spoken in the language it is printed in."],
        "do": [
            "Say **same** when both quotes report the same thing said, even though a translation never reads word for "
            "word.",
            "Say **translated** when a person is quoted in a language they were not speaking: a prime minister's Hindi "
            "speech printed in Kannada, a foreign leader printed in Tamil.",
            "Say **spoken so** when the occasion fits: a state minister talking to reporters in the state's language.",
            "Answer **Not sure** when the article does not tell you where or to whom it was said. It is a real answer.",
        ],
        "dont": [
            "Do not say **same** because two quotes are on the same subject. Two things one person said about one "
            "policy are two statements.",
            "Do not guess the language from the outlet alone. A Telugu paper quoting a Telugu minister prints the "
            "minister's own words; the same paper quoting the Prime Minister translates them.",
            "Do not judge whether the statement is true, fair or well said.",
        ],
        "examples_label": "Worked examples · invented",
        "examples": [
            {"mark": "yes", "head": "SAME — an English report and a Kannada report of a foreign leader’s speech",
             "body": "Both carry the one thing she said. Neither is in the language she spoke; both are translations "
                     "of it — and they are still the same statement."},
            {"mark": "no", "head": "TRANSLATED — a national leader’s Hindi speech, quoted in a Telugu paper",
             "body": "The speech was given in Hindi. The Telugu words are the paper’s own translation."},
            {"mark": "yes", "head": "SPOKEN SO — a Kannada minister, quoted in Kannada after a Bengaluru press meet",
             "body": "The occasion is a Kannada press meet; the quote is the minister’s own words."},
            {"head": "NOT SURE — a bilingual politician, quoted in English, with no hint of the occasion",
             "body": "Nothing in the article says which language was used. Guessing is worse than saying so."},
        ],
        "start": START,
        "after": None,
    },
}

KINDS = tuple(GUIDES)


def guide(kind: str) -> dict[str, Any] | None:
    """One kind's guide, with its kind named, or None for an unknown kind."""
    g = GUIDES.get(kind)
    return {"kind": kind, **g} if g else None
