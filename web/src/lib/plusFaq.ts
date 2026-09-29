// The Plus page's questions, in lib/ so a server route can read them too
// (PlusPage.tsx is a client module; /llms-full.txt and the FAQPage JSON-LD
// print exactly these strings).
import { GST_RATE } from "@/lib/billing";

export const FOUNDING_SEATS = 500; // common/billing.FOUNDING_CAP

export const CHECKOUT_SOON_FAQ = {
  q: "Can I subscribe today?",
  a: "Not yet. Checkout opens soon; until then nothing on this page can be bought and nothing is charged. The answers below are how Plus works once it opens, and reading stays free.",
};

export const PLUS_FAQ: { q: string; a: string }[] = [
  { q: "Does it renew on its own?", a: "Yes. Razorpay charges the price you joined at, at the start of every month or year, until you cancel. A new price only ever applies to a new subscription." },
  // common/billing.prices: founding is sold only on the launch offer and while seats remain.
  { q: "What is a founding membership?", a: `Everything in Plus, paid yearly at a lower price than Plus yearly, for the first ${FOUNDING_SEATS} members. It is sold only during the launch offer and while seats last. Your price is kept for as long as you stay subscribed, as Prism adds outlets and languages.` },
  { q: "Can I cancel?", a: "Yes, in one click from your account, any time. You keep Plus until the end of the period you paid for and are not charged again." },
  { q: "What if I change my mind?", a: "A yearly or founding charge is refunded in full if you ask within 7 days — no questions. Monthly charges are not refunded; cancelling stops the next one." },
  { q: "Who charges me, and how?", a: "Razorpay processes the payment (UPI Autopay, cards, net banking). It is collected by Matryx Social Labs Private Limited on behalf of Prism Media Intelligence LLP until the LLP's own merchant account is live, so that is the name you may see on your statement." },
  { q: "Is GST included?", a: `Yes. Every price on this page includes GST at ${Math.round(GST_RATE * 100)}%, and each plan shows how much of its price is GST. Each charge comes with an invoice by email.` },
  { q: "What if a charge fails?", a: "Plus stays on for three days while Razorpay tries again, and we email you. If it still fails, Plus pauses and reading stays free." },
  { q: "What does Plus not change?", a: "The record. Every record, source, quote, coverage split and clip stays free for everyone, with or without an account. Plus adds every lens on every story and more of Ask." },
  // Positioning (founder, 2026-09-29): reading costs scale with the outlets read,
  // not with readers (docs/marketing/MARKETING-PLAN.md § Pricing), so this is true.
  { q: "What does my subscription pay for?", a: "Reading more of India's news. Every outlet Prism monitors costs money to read and check each day, so Plus is what lets Prism add outlets and Indian languages to a record that stays free for everyone." },
];
