// The three legal documents, as data. Prose lives here so the three routes
// and the renderer stay trivial, and so a change to one clause is one diff.
// Every statement below describes what the code actually does (common/auth.py,
// common/quota.py, agent/rag.py, lib/session.ts, lib/returning.ts); when the
// product changes, this file changes in the same commit. Facts about the
// company (entity, contact, city) are the constants at the top.

export const LEGAL_ENTITY = "Matryx Social Labs";
export const CONTACT_EMAIL = "hello@readprism.news";
export const LEGAL_CITY = "Bengaluru, Karnataka";
export const LEGAL_UPDATED = "2026-09-20";

/** A paragraph, or a bullet list. */
export type Block = string | string[];
export type Section = { heading: string; blocks: Block[] };
export type LegalDoc = { slug: "privacy" | "terms" | "refunds"; title: string; lede: string; sections: Section[] };

export const PRIVACY: LegalDoc = {
  slug: "privacy",
  title: "Privacy policy",
  lede: `Prism is run by ${LEGAL_ENTITY}. This page says what we collect, why, where it goes, and how to have it removed. It is written to India's Digital Personal Data Protection Act, 2023.`,
  sections: [
    {
      heading: "What we collect",
      blocks: [
        "Reading without an account: nothing that identifies you. One cookie, prism.returning, tells the front page you have been here before so it can take you straight to the chart. Your browser keeps a few settings on your device (theme, the scope you last chose, the last story you opened) and sends them nowhere.",
        "Asking a question without an account: the question and the answer are stored against a random session id that lives in your browser. To keep the free box open for everyone we count questions per session and per hashed IP address; the hash cannot be turned back into your address and the counter expires within a day.",
        "An account: your email address, from the sign-in link you click or from Google if you sign in with Google. From Google we receive your email and the fact that Google has verified it, nothing else. At onboarding you may tell us your name, profession, state and reading languages, and we record the time you agreed to the Terms.",
        "What you do with an account: the tickers and sectors on your watchlist; the questions you ask and their answers, linked to your account; and, once paid plans exist, your plan, its status and the amount. We never see or store card or UPI details, the payment provider holds those.",
        "Technical records: our hosts keep ordinary server logs (IP address, browser, pages requested) for a short period to run and secure the service.",
      ],
    },
    {
      heading: "Why we collect it",
      blocks: [
        [
          "To sign you in and keep you signed in.",
          "To show you your state's news and your reading language.",
          "To answer your question and remember the thread.",
          "To apply fair-use limits on the question box.",
          "To bill you for a plan you chose and send its invoices.",
          "To send you the email you asked for: a sign-in link, and later a daily brief if you opt in.",
        ],
        "We do not sell personal data and we do not use it for advertising. We do not build profiles of you for anyone else.",
      ],
    },
    {
      heading: "Who processes it for us",
      blocks: [
        [
          "Vercel hosts the website.",
          "Railway hosts the API and the database.",
          "Resend delivers our email.",
          "Google, only if you choose Sign in with Google.",
          "Razorpay processes payments, once paid plans are on sale.",
          "OpenRouter, and the model providers it routes to, receive the text of a question in order to answer it. Your email and name are not sent with it.",
        ],
        "Some of these providers run servers outside India. Each is bound by its own contract to process data only on our instructions.",
      ],
    },
    {
      heading: "Cookies and device storage",
      blocks: [
        "One cookie, prism.returning, for routing a returning reader. On your device: your session token, your profile, your theme, your last scope and your last opened story. There are no advertising cookies and no cross-site tracking. If we add usage analytics we will use a tool that sets no cookies, and say so here.",
      ],
    },
    {
      heading: "How long we keep it",
      blocks: [
        [
          "A sign-in link works for 15 minutes and once.",
          "A session lasts 30 days unless you sign out.",
          "Account data stays until you delete the account.",
          "Anonymous questions stay against their random session id only.",
          "Billing records stay as long as tax law requires.",
        ],
      ],
    },
    {
      heading: "Your rights",
      blocks: [
        `You can ask what we hold about you, have it corrected, have it erased, or withdraw your consent, which closes the account. You can nominate someone to exercise these rights for you. Write to ${CONTACT_EMAIL} from the address on the account; we act within 30 days. If you are not satisfied you may complain to the Data Protection Board of India.`,
      ],
    },
    {
      heading: "Children",
      blocks: ["Prism is not for anyone under 18, and we do not knowingly hold data about a child. If you believe we do, write to us and we will remove it."],
    },
    {
      heading: "Security",
      blocks: ["Everything travels over HTTPS. Sign-in links and session tokens are stored only as hashes. Access to production data is limited to the people who run the service."],
    },
    {
      heading: "Changes",
      blocks: ["This page carries the date it last changed. If a change matters to you, we will say so at sign-in before it applies."],
    },
    {
      heading: "Contact",
      blocks: [`${LEGAL_ENTITY} · ${CONTACT_EMAIL}. The same address reaches our grievance officer.`],
    },
  ],
};

export const TERMS: LegalDoc = {
  slug: "terms",
  title: "Terms of service",
  lede: `These are the terms between you and ${LEGAL_ENTITY} for using Prism at readprism.news. They are short on purpose. Using Prism means you accept them.`,
  sections: [
    {
      heading: "What Prism is",
      blocks: [
        "Prism is an index of published news reports. It groups reports of one event into one record, counts which outlets covered it, prints what people said in their own words, and writes a short brief from those reports by machine. Every report links to the outlet that published it. Photographs belong to the outlets and open their reports.",
      ],
    },
    {
      heading: "Your account",
      blocks: [
        "You must be 18 or older. Your account is yours alone; keep the email address it is tied to secure, since a sign-in link sent to it is a key. Tell us if you think someone else has used it.",
      ],
    },
    {
      heading: "Fair use",
      blocks: [
        "Read as much as you like. Do not scrape, crawl or bulk-download Prism; do not drive the question box with a script; do not resell access or our text; do not try to get around a limit. We may suspend an account that does.",
      ],
    },
    {
      heading: "Content and rights",
      blocks: [
        "The reports belong to the outlets that published them. We link to them and quote short passages under fair dealing, with attribution. The text Prism writes (briefs, summaries, the structure of a record) belongs to us. You may share links and short excerpts with attribution to Prism and to the outlet.",
        `An outlet that wants a report removed from the index can write to ${CONTACT_EMAIL}; we act on such requests promptly.`,
      ],
    },
    {
      heading: "Text written by a machine",
      blocks: [
        "Briefs, summaries and answers in the question box are generated by a language model from the linked reports. They can be wrong. Check the reports before you rely on anything, and treat a quote as belonging to the report it is linked to. Nothing on Prism is investment, legal or medical advice; a market read is information, not a recommendation.",
      ],
    },
    {
      heading: "Paid plans",
      blocks: [
        "The price you see when you subscribe includes GST. A plan renews at the end of each period until you cancel; cancelling takes one click on your account page and access continues to the end of the period you paid for. Refunds follow the Refund policy. If a price changes, we tell you before the renewal it applies to.",
      ],
    },
    {
      heading: "Availability",
      blocks: [
        "Prism is provided as it is. We may change, add or remove features, and we do not promise uninterrupted service. We will give notice before discontinuing something you pay for.",
      ],
    },
    {
      heading: "Liability",
      blocks: [
        "To the extent the law allows, we are not liable for indirect or consequential loss arising from your use of Prism, and our total liability to you is limited to what you paid us in the twelve months before the claim.",
      ],
    },
    {
      heading: "Ending things",
      blocks: [
        "You can delete your account at any time by writing to us. We can suspend or close an account that breaks these terms, and will say why.",
      ],
    },
    {
      heading: "Law",
      blocks: [`Indian law governs these terms. Disputes go to the courts at ${LEGAL_CITY}.`],
    },
    {
      heading: "Contact",
      blocks: [`${LEGAL_ENTITY} · ${CONTACT_EMAIL}`],
    },
  ],
};

export const REFUNDS: LegalDoc = {
  slug: "refunds",
  title: "Refund policy",
  lede: "Paid plans are not yet on sale. This policy applies from the day they are.",
  sections: [
    {
      heading: "Monthly plans",
      blocks: [
        "A paid month is not refunded. Cancel at any time from your account page; you keep access until the end of the month you paid for and are not charged again.",
      ],
    },
    {
      heading: "Annual and founding plans",
      blocks: [
        "Ask within 7 days of an annual charge and we refund it in full, no questions asked. This applies to the first charge and to each renewal. After 7 days the remainder of the year is not refunded, but cancelling stops the next renewal.",
      ],
    },
    {
      heading: "Mistaken and duplicate charges",
      blocks: ["A charge made in error, a duplicate, or a charge after you cancelled is refunded in full whenever you tell us."],
    },
    {
      heading: "How to ask",
      blocks: [
        `Write to ${CONTACT_EMAIL} from the email on the account, with the payment reference from your invoice. We issue the refund within 5 working days to the method you paid with; your bank or UPI app may take a few more days to show it.`,
      ],
    },
  ],
};

export const LEGAL_DOCS: LegalDoc[] = [PRIVACY, TERMS, REFUNDS];
