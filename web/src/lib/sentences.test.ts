import { describe, expect, it } from "vitest";
import { sentences } from "@/lib/sentences";

describe("sentences", () => {
  it("does not end a sentence on an initial or an abbreviation", () => {
    expect(sentences("Tata Trusts has declared the reappointment of N. Chandrasekaran invalid. The Trusts argue it breached the Articles.")).toEqual([
      "Tata Trusts has declared the reappointment of N. Chandrasekaran invalid.",
      "The Trusts argue it breached the Articles.",
    ]);
    expect(sentences("The fee is Rs. 500 a month. Dr. Rao disagreed.")).toEqual(["The fee is Rs. 500 a month.", "Dr. Rao disagreed."]);
  });

  it("still splits ordinary sentences, and keeps a closing quote with its sentence", () => {
    expect(sentences("It rained. “We object,” he said. Then it stopped!")).toEqual(["It rained.", "“We object,” he said.", "Then it stopped!"]);
  });
});
