import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { REFUSALS, WORDS } from "@/components/HowItWorks";
import { LANDING_FAQ } from "@/lib/faq";
import { PLUS_FAQ } from "@/lib/plusFaq";

// llms.txt at length (audit 01 P2-8): its body, then the landing's questions,
// what Prism refuses and the words a record uses, each exactly as the pages
// print them. Built once at deploy and served as a file: no function runs when
// an agent reads it, and no Accept: text/markdown negotiation.
// The Plus questions come from lib/plusFaq, not PlusPage.tsx: a route handler
// importing from a "use client" module gets a client reference, not the array.
export const dynamic = "force-static";

const section = (title: string, lines: string[]) => [`## ${title}`, "", ...lines, ""].join("\n");

export async function GET(): Promise<Response> {
  const llms = await readFile(join(process.cwd(), "public", "llms.txt"), "utf8");
  const body = [
    llms.trimEnd(),
    "",
    section("Questions a first visit asks", LANDING_FAQ.map(({ q, a }) => `### ${q}\n\n${a}\n`)),
    section("Plus: questions before you pay", PLUS_FAQ.map(({ q, a }) => `### ${q}\n\n${a}\n`)),
    section("What Prism refuses to do", REFUSALS.map(([rule, why]) => `- ${rule} ${why}`)),
    section("The words on a record", WORDS.map(([term, meaning]) => `- ${term}: ${meaning}`)),
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
