import { describe, expect, it } from "vitest";
import type { ClaimOut } from "@/lib/api";
import { findQuote, orderForReader, quoteId, unitsForReader } from "@/lib/quotes";

const q = (quote_text: string, lang: string | null): ClaimOut => ({
  quote_text,
  quote_start: null,
  quote_end: null,
  article_id: quote_text,
  source_name: "Outlet",
  url: null,
  published_at: null,
  lang,
});

describe("orderForReader", () => {
  it("lifts the reader's language to the front of the rotation", () => {
    // The API order is English-first for a reader who said nothing.
    const claims = [q("english", "en"), q("kannada one", "kn"), q("kannada two", "kn")];
    expect(orderForReader(claims, ["kn"]).map((x) => x.claim.quote_text)).toEqual([
      "kannada one",
      "english",
      "kannada two",
    ]);
  });

  it("keeps each quote's position in the API's array", () => {
    // quoteId addresses a quote by index and the OG card resolves that index
    // against the API's own order — renumbering would hand a Kannada reader a
    // share link whose card shows a different sentence.
    const claims = [q("english", "en"), q("kannada", "kn")];
    const first = orderForReader(claims, ["kn"])[0];
    expect(first.claim.quote_text).toBe("kannada");
    expect(first.index).toBe(1);
    expect(quoteId(0, first.index)).toBe("0-1");
    expect(findQuote([{ speaker: "X", claims, languages: ["en", "kn"] }], "0-1")?.claim.quote_text)
      .toBe("kannada");
  });

  it("leaves a single-language speaker exactly as the API ordered them", () => {
    const claims = [q("newer", "kn"), q("older", "kn")];
    expect(orderForReader(claims, ["en"]).map((x) => x.claim.quote_text)).toEqual(["newer", "older"]);
  });

  it("changes nothing for a reader who has expressed no preference", () => {
    const claims = [q("english", "en"), q("kannada", "kn")];
    expect(orderForReader(claims, []).map((x) => x.claim.quote_text)).toEqual(["english", "kannada"]);
  });

  it("does not lose a quote whose article carried no language", () => {
    const claims = [q("tagged", "en"), q("untagged", null)];
    expect(orderForReader(claims, ["kn"]).map((x) => x.claim.quote_text).sort()).toEqual([
      "tagged",
      "untagged",
    ]);
  });
});

describe("unitsForReader", () => {
  it("collapses renderings of one utterance under the one this reader meets first", () => {
    const claims = [
      { ...q("english", "en"), utterance: "u" },
      { ...q("kannada", "kn"), utterance: "u" },
      q("other", "en"),
    ];
    const units = unitsForReader(claims, ["kn"]);
    expect(units.map((u) => u.lead.claim.quote_text)).toEqual(["kannada", "other"]);
    expect(units[0].also.map((a) => a.claim.quote_text)).toEqual(["english"]);
    // Every rendering keeps its API position: it is the share address.
    expect(units[0].also[0].index).toBe(0);
  });

  it("is one unit per quote when nothing has been judged", () => {
    const claims = [q("a", "en"), q("b", "kn")];
    expect(unitsForReader(claims, []).map((u) => u.also.length)).toEqual([0, 0]);
  });
});
