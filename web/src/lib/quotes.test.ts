import { describe, expect, it } from "vitest";
import type { ClaimOut, SpeakerClaims } from "@/lib/api";
import { findQuote, orderForReader, quoteId, quoteOutlets, saidCount, saidWords, showcaseQuote, unitsForReader } from "@/lib/quotes";

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

// A quote's address is its words (the API's `id`), so a newer report can no
// longer renumber a link someone shared. Links shared before 27 Sep 2026 named
// a position; the API maps each to the quote now holding its words.
const said = (id: string, text: string, extra: Partial<ClaimOut> = {}): ClaimOut => ({ ...q(text, "en"), id, ...extra });
const groups: SpeakerClaims[] = [
  { speaker: "Bikram Singh Majithia", role: "Akali Dal leader", claims: [said("m1", "The accused should face the strictest punishment")] },
  {
    speaker: "Gaurav Toora",
    role: null,
    claims: [said("t1", "When we reached here, we came to know", { also_in: [{ id: "t1b", article_id: "x", source_name: "The Hindu", url: null, published_at: null }] })],
  },
];

describe("findQuote", () => {
  it("finds a quote by its words' id, or by the id of another outlet's copy of them", () => {
    expect(findQuote(groups, "t1")?.speaker).toBe("Gaurav Toora");
    expect(findQuote(groups, "t1b")?.claim.id).toBe("t1");
  });

  it("resolves a link shared before the checks to the quote now holding its words", () => {
    // Before, Toora's card came first and printed Majithia's words as 0-1.
    const aliases = { "0-0": "t1", "0-1": "m1" };
    expect(findQuote(groups, "0-1", aliases)?.speaker).toBe("Bikram Singh Majithia");
    expect(findQuote(groups, "0-1", aliases)?.id).toBe("m1");
  });

  it("finds nothing for a position whose quote was withdrawn", () => {
    expect(findQuote(groups, "0-2", { "0-0": "t1" })).toBeNull();
  });

  it("still reads a position against an older payload that carries no aliases", () => {
    expect(findQuote(groups, "1-0")?.claim.id).toBe("t1");
  });
});

describe("quoteOutlets", () => {
  it("counts the outlets that carried a quote as well as the one it cites", () => {
    expect(quoteOutlets(groups[1].claims)).toBe(2);
  });
});

describe("showcaseQuote", () => {
  it("leads with a quote two outlets carried, not the record's first", () => {
    expect(showcaseQuote(groups)?.claims[0].id).toBe("t1");
  });

  it("falls back to a speaker the articles name an office for", () => {
    const single = [
      { speaker: "Someone", role: null, claims: [said("s1", "A single outlet quote")] },
      { speaker: "Naveen Singla", role: "DIG Jalandhar Range", claims: [said("n1", "We are verifying the facts")] },
    ];
    expect(showcaseQuote(single)?.speaker).toBe("Naveen Singla");
    expect(showcaseQuote([])).toBeNull();
  });
});

// Reported speech (founder decision 28 Sep): an Indian-language article's
// "X said that…" is shown, labelled, and never printed as a quote.
describe("reported speech", () => {
  const reported = said("r1", "ಪೌರಕಾರ್ಮಿಕ ಪಾತ್ರ ಅತ್ಯಂತ ಮಹತ್ವದ್ದಾಗಿದೆ", { speech: "reported" });

  it("never wraps reported words in quotation marks; a quote keeps its marks", () => {
    expect(saidWords(reported)).toBe("ಪೌರಕಾರ್ಮಿಕ ಪಾತ್ರ ಅತ್ಯಂತ ಮಹತ್ವದ್ದಾಗಿದೆ");
    expect(saidWords(said("q1", "We will reopen the bridge"))).toBe("“We will reopen the bridge”");
    expect(saidWords(said("q2", "We will reopen the bridge on Monday"), 10)).toBe("“We will r…”");
  });

  it("counts quotes and reported words apart", () => {
    expect(saidCount([said("a", "one"), said("b", "two"), reported])).toBe("2 quotes · 1 reported");
    expect(saidCount([said("a", "one")])).toBe("1 quote");
    expect(saidCount([reported])).toBe("1 reported");
  });

  it("is never the showcase: the landing shows a quote", () => {
    const only = [{ speaker: "Sangappa", role: "Deputy commissioner", claims: [{ ...reported, also_in: [{ id: "x", article_id: "x", source_name: "Vijay Karnataka", url: null, published_at: null }] }] }];
    expect(showcaseQuote(only)).toBeNull();
    expect(showcaseQuote([...only, ...groups])?.claims[0].id).toBe("t1");
  });
});
