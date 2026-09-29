// The questions a first visitor asks, answered on the landing and, word for
// word, in its FAQPage JSON-LD (lib/seo faqLd): the markup must equal the
// visible text. Every answer is checked against the code it describes; no
// number is typed and no lens is named (the lens set grows).
import { CONTACT_EMAIL } from "@/lib/legal";

export type Faq = { q: string; a: string };

export const LANDING_FAQ: Faq[] = [
  {
    q: "What is Prism?",
    a: "Prism reads Indian news from a public list of outlets, in English and Indian languages, and keeps one page per story: every report it found, who said what in their exact words, and which outlets covered it.",
  },
  {
    q: "Is it free? Do I need an account?",
    a: "Reading is free, with or without an account: every story, every report behind it, every verified quote, the coverage count and every correction. An account (a one-time sign-in link by email, no password) gives you more questions and professional readings each day.",
  },
  {
    q: "Which outlets does Prism read?",
    a: "A fixed list, published in full on the Sources page with when each outlet was last read. Every count on a story is out of that list, never out of everyone who covered it.",
  },
  {
    q: "Which languages?",
    a: "Prism reads outlets in English and in Indian languages; the Sources page lists them by language. Prism writes its own headlines and briefs in English. Reports and quotes stay in the language they were published in.",
  },
  {
    q: "Are the quotes real?",
    a: "A quote appears only when the article it came from prints the same words inside quotation marks, and it opens the article at that line. If the check fails, the quote is dropped, never paraphrased. Words an Indian-language report attributes without quotation marks are labelled “reported” and never set as a quote.",
  },
  {
    q: "Who writes the headlines and briefs?",
    a: "Software writes them from the reports listed underneath, and every page says so. Where a brief says why a story matters, that is Prism’s reading, and it is labelled. The reporting belongs to the outlets; Prism links to each report.",
  },
  {
    q: "Does Prism take sides or rate outlets?",
    a: "No. Prism does not rate an outlet’s politics or a report’s tone. It shows which outlets covered a story, grouped by where they come from (English national, Indian-language, international, wire), and lets you read each report.",
  },
  {
    q: "How is this different from a news app?",
    a: "Most news apps give you a list of headlines or a short summary. Prism gives each story one page with every report it found, the exact words people said, and a count of who covered it out of a public list, so you can check the story for yourself.",
  },
  {
    // app/manifest.ts: installable (display standalone), start_url /feed, which is Today.
    q: "Is there an app?",
    a: "Not in an app store. On a phone, open readprism.news in your browser and add it to your home screen from the browser menu; it then opens on Today like an app.",
  },
  {
    q: "What if Prism gets something wrong?",
    a: `Use “Something wrong?” at the foot of any story, or write to ${CONTACT_EMAIL} with its link. A correction is shown on the story with the date and the reason, and listed on the Corrections page. Every earlier version of a story page is kept.`,
  },
];
