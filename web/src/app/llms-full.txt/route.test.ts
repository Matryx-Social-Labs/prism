// @vitest-environment node
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { PLUS_FAQ } from "@/lib/plusFaq";
import { REFUSALS, WORDS } from "@/components/HowItWorks";
import { LANDING_FAQ } from "@/lib/faq";
import { GET, dynamic } from "./route";

describe("/llms-full.txt", () => {
  // Audit 01 P2-8: a build output, never a function invocation per agent read.
  it("is built statically", () => {
    expect(dynamic).toBe("force-static");
  });

  it("is llms.txt, then the landing FAQ, the refusals and the glossary, word for word", async () => {
    const res = await GET();
    expect(res.headers.get("content-type")).toBe("text/plain; charset=utf-8");
    const text = await res.text();
    expect(text.startsWith(readFileSync(join(process.cwd(), "public", "llms.txt"), "utf8").trimEnd())).toBe(true);
    for (const { q, a } of LANDING_FAQ) expect(text).toContain(`### ${q}\n\n${a}\n`);
    for (const { q, a } of PLUS_FAQ) expect(text).toContain(`### ${q}\n\n${a}\n`);
    expect(text).toContain("### Is there an app?");
    for (const [rule, why] of REFUSALS) expect(text).toContain(`- ${rule} ${why}`);
    for (const [term, meaning] of WORDS) expect(text).toContain(`- ${term}: ${meaning}`);
  });

  it("is linked from llms.txt", () => {
    expect(readFileSync(join(process.cwd(), "public", "llms.txt"), "utf8")).toContain("https://www.readprism.news/llms-full.txt");
  });
});
