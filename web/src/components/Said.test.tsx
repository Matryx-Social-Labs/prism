import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { ClaimOut, SpeakerClaims } from "@/lib/api";
import { Said } from "@/components/Said";

const claim = (quote_text: string, lang: string | null, source_name = "Outlet"): ClaimOut => ({
  quote_text,
  quote_start: null,
  quote_end: null,
  article_id: quote_text,
  source_name,
  url: "https://o.example/a",
  published_at: null,
  lang,
});

const index = (sp: SpeakerClaims) =>
  new Map(sp.claims.map((c, i) => [c.article_id, i + 1]));

afterEach(() => window.localStorage.clear());

describe("the quote card and the language its words were printed in", () => {
  it("names the language on every quote when the card holds more than one", () => {
    const sp: SpeakerClaims = {
      speaker: "Donald Trump",
      claims: [claim("what he said", "en", "Times of India"), claim("ಅವರು ಹೇಳಿದ್ದು", "kn", "TV9 Kannada")],
      languages: ["en", "kn"],
    };
    render(<Said claims={[sp]} sourceIndex={index(sp)} />);
    expect(screen.getByText("EN")).toBeInTheDocument();
    expect(screen.getByText("ಕನ್ನಡ")).toBeInTheDocument();
    expect(screen.getByText(/2 languages/)).toBeInTheDocument();
  });

  it("says nothing about language when every quote is in the same one", () => {
    // 43% of stored quotes are non-English ORIGINALS. A lone Kannada card is the
    // ordinary case and a label there answers a question nobody asked.
    const sp: SpeakerClaims = {
      speaker: "Siddaramaiah",
      claims: [claim("ಅವರು ಹೇಳಿದ್ದು", "kn", "Prajavani")],
      languages: ["kn"],
    };
    render(<Said claims={[sp]} sourceIndex={index(sp)} />);
    expect(screen.queryByText("ಕನ್ನಡ")).not.toBeInTheDocument();
    expect(screen.queryByText(/languages/)).not.toBeInTheDocument();
  });

  it("leads with the reader's own language and keeps the original on the card", () => {
    window.localStorage.setItem(
      "prism.profile.v1",
      JSON.stringify({ lens: "reader", region: null, state: null, interests: [], languages: ["kn"] }),
    );
    const sp: SpeakerClaims = {
      speaker: "Donald Trump",
      claims: [claim("what he said", "en"), claim("ಅವರು ಹೇಳಿದ್ದು", "kn")],
      languages: ["en", "kn"],
    };
    render(<Said claims={[sp]} sourceIndex={index(sp)} />);
    const quotes = screen.getAllByText(/“/).map((n) => n.textContent);
    expect(quotes[0]).toContain("ಅವರು ಹೇಳಿದ್ದು");
    // D-quote-2: the reader's rendering does not replace the original, it sits beside it.
    expect(quotes[1]).toContain("what he said");
  });
});
