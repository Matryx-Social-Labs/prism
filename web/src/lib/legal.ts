// The three legal documents, as data. Prose lives here so the three routes
// and the renderer stay trivial, and so a change to one clause is one diff.
// Every statement below describes what the code actually does (common/auth.py,
// common/quota.py, agent/rag.py, lib/session.ts, lib/returning.ts); when the
// product changes, this file changes in the same commit. Facts about the
// company (entity, contact, city) are the constants at the top.

// Who is who: Prism Media Intelligence LLP owns and operates Prism and is the
// data fiduciary; Matryx Social Labs Private Limited (brand: Matrix Social
// Labs) builds and runs it as the technology partner, and so is a processor.
export const LEGAL_ENTITY = "Prism Media Intelligence LLP";
export const LEGAL_PARTNER = "Matryx Social Labs Private Limited (Matrix Social Labs)";
export const CONTACT_EMAIL = "hello@readprism.news";
export const LEGAL_CITY = "Bengaluru, Karnataka";
export const LEGAL_UPDATED = "2026-09-24";

/** A paragraph, or a bullet list. */
export type Block = string | string[];
/** `short`: the section in one plain sentence, printed under its heading. */
export type Section = { heading: string; short?: string; blocks: Block[] };
export type LegalDoc = {
  slug: "privacy" | "terms" | "refunds";
  title: string;
  kind: string; // the mono label: Policy · Terms
  lede: string;
  /** The whole document in a few plain lines, for the rail and the phone's top. */
  inShort: string[];
  sections: Section[];
};

/** A stable anchor for a section heading. */
export const anchor = (heading: string) => heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

export const PRIVACY: LegalDoc = {
  slug: "privacy",
  title: "Privacy policy",
  kind: "Policy",
  inShort: [
    "Read without an account and we keep no history of what you read.",
    "An account is your email, plus what you choose to tell us at onboarding.",
    "Your questions are stored to keep the thread; nothing is sold or used for ads.",
    "Ask, and we delete it all.",
  ],
  lede: `Prism is owned and operated by ${LEGAL_ENTITY} ("Prism", "we"), and built and run with ${LEGAL_PARTNER} as its technology partner. This page says what we collect, why, where it goes, and how to have it removed. It is written to India's Digital Personal Data Protection Act, 2023 and its Rules ahead of the dates their main duties begin, and under them ${LEGAL_ENTITY} is the data fiduciary.`,
  sections: [
    {
      heading: "What we collect",
      short: "No history of what you read; your email and what you tell us once you sign in.",
      blocks: [
        "Reading without an account: we keep no history of what you read, and nothing in our database identifies you. One cookie, prism.returning, tells the front page you have been here before so it can take you straight to the chart. Your browser keeps a few settings on your device (theme, the scope you last chose, the last story you opened) and sends them nowhere.",
        "How Prism is used, counted without knowing who: we count page views and a handful of actions (opening a lens, asking a question, sharing, each step of subscribing) as daily totals by kind. A kind of page, never which story; how a question was opened, never the question; the site a visit came from, never the page. To count how many people visited in a day, we hash your IP address and browser with a random value that is replaced every day and deleted within two days; the hash is used only for that day's count, never stored in our database, and cannot be linked to you or to another day. None of this sets a cookie.",
        "Asking a question without an account: the question and the answer are stored against a random session id that lives in your browser. To keep the free box open for everyone we count questions per session and per IP address, hashed with a value that changes every day, so the hash cannot be turned back into your address; the counter expires after about a day (26 hours).",
        "An account: signing in sets one cookie, prism_session, that keeps you signed in for 30 days; it is marked so that no script on the page can read it, and signing out deletes it. Your email address, from the sign-in link you click or from Google if you sign in with Google. From Google we receive your email and the fact that Google has verified it, nothing else. At onboarding you may tell us your name, profession, state and reading languages, and we record the time you agreed to the Terms.",
        "What you do with an account: the tickers and sectors on your watchlist; the questions you ask and their answers, linked to your account; the days on which you used Prism while signed in (the date only, never what you read), so we can see how many readers come back; and, once paid plans exist, your plan, its status and the amount. We never see or store card or UPI details, the payment provider holds those.",
        "Technical records: our hosts keep ordinary server logs (IP address, browser, pages requested) for a short period to run and secure the service.",
      ],
    },
    {
      heading: "Why we collect it",
      short: "To sign you in, show your state, answer your questions and bill you — nothing else.",
      blocks: [
        [
          "To sign you in and keep you signed in.",
          "To show you your state's news and your reading language.",
          "To answer your question and remember the thread.",
          "To apply fair-use limits on the question box.",
          "To count, in totals, how Prism is used and how many readers come back, so we know what to build.",
          "To bill you for a plan you chose and send its invoices.",
          "To send you the email you asked for: a sign-in link, and later a daily brief if you opt in.",
        ],
        "We do not sell personal data and we do not use it for advertising. We do not build profiles of you for anyone else.",
      ],
    },
    {
      heading: "Who processes it for us",
      short: "Our hosts, our email provider, Google if you use it, Razorpay when you pay, and the model that answers your question.",
      blocks: [
        [
          `${LEGAL_PARTNER} engineers and operates the service for us, and so has access to production systems on our instructions.`,
          "Vercel hosts the website.",
          "Railway hosts the API and the database.",
          "Resend delivers our email.",
          "Google, only if you choose Sign in with Google.",
          "Razorpay processes payments, once paid plans are on sale.",
          "OpenRouter, and the model providers it routes to, receive the text of a question in order to answer it. Your email and name are not sent with it. Every question is sent with OpenRouter's instruction to use only providers that do not store or train on it; a provider that does not accept that instruction is not used. Do not put personal or confidential details in a question.",
        ],
        "Some of these providers run servers outside India. Each is bound by its own contract to process data only on our instructions.",
      ],
    },
    {
      heading: "Cookies and device storage",
      short: "One routing cookie and a few settings on your device. No trackers.",
      blocks: [
        "One cookie, prism.returning, for routing a returning reader. On your device: your session token, your profile, your theme, your last scope and your last opened story; a marker that this tab's visit has already been counted; and, when you are signed in, the date your account was last counted as active, so it is counted once a day. There are no advertising cookies and no cross-site tracking. Usage is counted without cookies, as “What we collect” describes.",
      ],
    },
    {
      heading: "How long we keep it",
      short: "Links minutes, sessions a month, accounts until you delete them.",
      blocks: [
        [
          "A sign-in link works for 15 minutes and once.",
          "A session lasts 30 days unless you sign out.",
          "Account data stays until you delete the account.",
          "Anonymous questions stay against their random session id only.",
          "Daily usage totals are kept; they hold nothing about a person. The days an account was active are deleted with the account.",
          "Billing records stay as long as tax law requires.",
        ],
      ],
    },
    {
      heading: "Your rights",
      short: "See it, fix it, erase it, take it back — one email.",
      blocks: [
        `You can ask what we hold about you, have it corrected, have it erased, or withdraw your consent, which closes the account. You can nominate someone to exercise these rights for you. Write to ${CONTACT_EMAIL} from the address on the account; we act within 30 days. If you are not satisfied you may complain to the Data Protection Board of India.`,
      ],
    },
    {
      heading: "Children",
      short: "Prism is for adults.",
      blocks: ["Prism is not for anyone under 18, and we do not knowingly hold data about a child. If you believe we do, write to us and we will remove it."],
    },
    {
      heading: "Security",
      short: "HTTPS everywhere; secrets stored only as hashes.",
      blocks: ["Everything travels over HTTPS. Sign-in links and session tokens are stored only as hashes. Access to production data is limited to the people who run the service."],
    },
    {
      heading: "Changes",
      short: "Dated here; the ones that matter, announced at sign-in.",
      blocks: ["This page carries the date it last changed. If a change matters to you, we will say so at sign-in before it applies."],
    },
    {
      heading: "Contact",
      short: "One address for everything, including grievances.",
      blocks: [`${LEGAL_ENTITY} · ${CONTACT_EMAIL}. The same address reaches our grievance officer. Matters about the engineering of the service reach ${LEGAL_PARTNER} through us.`],
    },
  ],
};

export const TERMS: LegalDoc = {
  slug: "terms",
  title: "Terms of service",
  kind: "Terms",
  inShort: [
    "Prism indexes published reports and links every one of them.",
    "Reading is free; be 18, keep your sign-in email safe, do not scrape.",
    "Briefs and answers are written by a machine from the reports — check them.",
    "Paid plans renew until you cancel, in one click, with access to the period's end.",
  ],
  lede: `These are the terms between you and ${LEGAL_ENTITY}, which owns and operates Prism at readprism.news (built and run with ${LEGAL_PARTNER}). They are short on purpose. Using Prism means you accept them.`,
  sections: [
    {
      heading: "What Prism is",
      short: "An index of reports, grouped by event, with quotes verbatim and a machine-written brief.",
      blocks: [
        "Prism is an index of published news reports. It groups reports of one event into one record, counts which outlets covered it, prints what people said in their own words, and writes a short brief from those reports by machine. Every report links to the outlet that published it. Photographs belong to the outlets and open their reports.",
      ],
    },
    {
      heading: "Your account",
      short: "18 or older; your sign-in email is the key.",
      blocks: [
        "You must be 18 or older. Your account is yours alone; keep the email address it is tied to secure, since a sign-in link sent to it is a key. Tell us if you think someone else has used it.",
      ],
    },
    {
      heading: "Fair use",
      short: "Read all you like; do not scrape, script or resell.",
      blocks: [
        "Read as much as you like. Do not scrape, crawl or bulk-download Prism; do not drive the question box with a script; do not resell access or our text; do not try to get around a limit. We may suspend an account that does.",
      ],
    },
    {
      heading: "Content and rights",
      short: "The reports are the outlets'; our text is ours; share with attribution.",
      blocks: [
        "The reports belong to the outlets that published them. We link to them and quote short passages under fair dealing, with attribution. The text Prism writes (briefs, summaries, the structure of a record) belongs to us. You may share links and short excerpts with attribution to Prism and to the outlet.",
        `An outlet that wants a report removed from the index can write to ${CONTACT_EMAIL}; we act on such requests promptly.`,
      ],
    },
    {
      heading: "Text written by a machine",
      short: "Briefs and answers can be wrong; the linked reports are the record.",
      blocks: [
        "Briefs, summaries and answers in the question box are generated by a language model from the linked reports. They can be wrong. Check the reports before you rely on anything, and treat a quote as belonging to the report it is linked to. Nothing on Prism is investment, legal or medical advice; a market read is information, not a recommendation.",
      ],
    },
    {
      heading: "Paid plans",
      short: "GST-inclusive prices, renewing until you cancel; refunds per the Refund policy.",
      blocks: [
        "The price you see when you subscribe includes GST. A plan renews at the end of each period until you cancel; cancelling takes one click on your account page and access continues to the end of the period you paid for. Refunds follow the Refund policy. If a price changes, we tell you before the renewal it applies to.",
        `Payments are processed by Razorpay and collected by ${LEGAL_PARTNER} on behalf of ${LEGAL_ENTITY} until the LLP's own merchant account is live; that is the name you may see on your statement.`,
      ],
    },
    {
      heading: "Availability",
      short: "As it is; features change; notice before anything paid is withdrawn.",
      blocks: [
        "Prism is provided as it is. We may change, add or remove features, and we do not promise uninterrupted service. We will give notice before discontinuing something you pay for.",
      ],
    },
    {
      heading: "Liability",
      short: "Capped at what you paid us in the last twelve months.",
      blocks: [
        "To the extent the law allows, we are not liable for indirect or consequential loss arising from your use of Prism, and our total liability to you is limited to what you paid us in the twelve months before the claim.",
      ],
    },
    {
      heading: "Ending things",
      short: "You can leave any time; we can close an account that breaks these terms.",
      blocks: [
        "You can delete your account at any time by writing to us. We can suspend or close an account that breaks these terms, and will say why.",
      ],
    },
    {
      heading: "Law",
      short: "Indian law; the courts named below.",
      blocks: [`Indian law governs these terms. Disputes go to the courts at ${LEGAL_CITY}.`],
    },
    {
      heading: "Contact",
      short: "One address.",
      blocks: [`${LEGAL_ENTITY} · ${CONTACT_EMAIL}`],
    },
  ],
};

export const REFUNDS: LegalDoc = {
  slug: "refunds",
  title: "Refund policy",
  kind: "Policy",
  inShort: [
    "Monthly: not refunded; cancelling stops the next charge.",
    "Yearly and founding: refunded in full within 7 days of any charge — one click on your account page.",
    "Refunds go back the way you paid, through Razorpay, in 5–7 working days.",
    "Mistakes and duplicates: refunded whenever you tell us.",
  ],
  lede: `Paid plans are not yet on sale. This policy applies from the day they are. Payments are processed by Razorpay and collected by ${LEGAL_PARTNER} on behalf of ${LEGAL_ENTITY}.`,
  sections: [
    {
      heading: "Monthly plans",
      short: "A paid month is kept; cancel any time and you are not charged again.",
      blocks: [
        "A paid month is not refunded. Cancel at any time from your account page; you keep access until the end of the month you paid for and are not charged again.",
      ],
    },
    {
      heading: "Annual and founding plans",
      short: "Seven days from any yearly charge to take it all back, no questions asked.",
      blocks: [
        "For seven days after an annual or founding charge — the first one and every renewal — your account page shows a Refund button beside your plan. One click refunds that charge in full and ends Plus at once; we do not ask why. The window and the day it closes are printed on the plan card.",
        "After seven days the remainder of the year is not refunded, but cancelling stops the next renewal and you keep Plus to the end of the year you paid for.",
      ],
    },
    {
      heading: "How a refund reaches you",
      short: "Razorpay returns it to the card, account or UPI app you paid with; banks take 5–7 working days.",
      blocks: [
        "Every refund is made through Razorpay against the original payment, so it goes back to the same card, bank account or UPI app. Razorpay hands it to your bank the same day; most banks show it within 5–7 working days, and a few take up to 10. You get an email from us with the refund reference the moment it is made, and Razorpay's own confirmation follows.",
        "We cannot send a refund to a different account, and we cannot make it arrive faster than your bank does.",
      ],
    },
    {
      heading: "Mistaken and duplicate charges",
      short: "Told us? Refunded, whenever it happened.",
      blocks: ["A charge made in error, a duplicate, or a charge after you cancelled is refunded in full whenever you tell us, with no time limit."],
    },
    {
      heading: "How to ask",
      short: `Inside the window: the button on your account page. Anything else: ${CONTACT_EMAIL}.`,
      blocks: [
        `Inside the seven-day window, use the Refund button on your account page — it is the fastest route and needs nothing from you. For anything else, write to ${CONTACT_EMAIL} from the email on the account with the payment reference from your Razorpay receipt. We make the refund through Razorpay within 5 working days of your message, and it then reaches you as described above.`,
      ],
    },
  ],
};

export const LEGAL_DOCS: LegalDoc[] = [PRIVACY, TERMS, REFUNDS];
