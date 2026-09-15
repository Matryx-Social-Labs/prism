import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartRow, lensMarkers } from "@/components/ChartRow";
import type { FeedItem } from "@/lib/api";

function item(over: Partial<FeedItem> = {}): FeedItem {
  return {
    id: "e1",
    title: "Crime Branch to re-arrest Dr. M.K Ram",
    headline_lang: "en",
    available_languages: [],
    summary: "s",
    sector: "finance",
    subsector: null,
    regions: [],
    image_url: null,
    is_regional: false,
    coverage: { origins: { IN: 3, UK: 1 }, unknown: 0 },
    event_type: null,
    source_count: 4,
    cvss_score: null,
    cvss_severity: null,
    kev_listed: false,
    cve_ids: [],
    tickers: [],
    catalyst: null,
    price_impact_direction: null,
    last_updated_at: "2026-09-05T16:05:00Z",
    latest_published_at: "2026-09-05T16:05:00Z",
    score: 1,
    ...over,
  } as FeedItem;
}

const row = (it: FeedItem, props: Partial<Parameters<typeof ChartRow>[0]> = {}) =>
  render(
    <ol>
      <ChartRow item={it} {...props} />
    </ol>,
  );

describe("ChartRow — the label grid", () => {
  // The grammar: origin · time · code, every row, in that order. The time is the
  // news's own clock in IST, and the code is the six-sector group's, not the
  // pipeline's ten (finance prints BIZ).
  it("prints origin, IST time and the group code in that order", () => {
    row(item());
    const grid = screen.getByText("IN ×3 · UK ×1").parentElement!;
    expect([...grid.querySelectorAll("span")].map((s) => s.textContent)).toEqual(["IN ×3 · UK ×1", "21:35", "BIZ"]);
  });

  it('prints nothing for "other" — the taxonomy\'s failure is not a label', () => {
    row(item({ sector: "other" }));
    expect(screen.queryByText("OTHER")).toBeNull();
  });

  it("tags a headline in a script the reader did not choose, and only then", () => {
    row(item({ headline_lang: "kn" }), { primaryLang: "en" });
    expect(screen.getByText("ಕನ್ನಡ")).toBeInTheDocument();
    row(item({ id: "e2", headline_lang: "kn" }), { primaryLang: "kn" });
    expect(screen.getAllByText("ಕನ್ನಡ")).toHaveLength(1);
  });
});

describe("ChartRow — state is line form", () => {
  it("sets a single-source story on a dashed rule and says so", () => {
    const { container } = row(item({ source_count: 1 }));
    expect(container.querySelector("li")!.className).toBe("rule-single");
    expect(screen.getByText("1 source")).toBeInTheDocument();
    expect(screen.getByLabelText("1 source")).toBeInTheDocument();
  });

  it("sets a corroborated story on a solid rule with its count", () => {
    const { container } = row(item({ source_count: 8 }));
    expect(container.querySelector("li")!.className).toBe("rule-live");
    expect(screen.getByLabelText("8 sources")).toHaveTextContent("8");
    expect(screen.queryByText("1 source")).toBeNull();
  });

  it("marks the row the reader last opened", () => {
    row(item(), { lastOpened: true });
    expect(screen.getByRole("link")).toHaveAttribute("aria-current", "true");
  });
});

describe("ChartRow — the only colour is a lens marker", () => {
  it("shows a markets read when the pipeline found a ticker or a catalyst", () => {
    expect(lensMarkers(item({ tickers: ["RELIANCE"] })).map((m) => m.key)).toEqual(["markets"]);
    expect(lensMarkers(item({ catalyst: "earnings" })).map((m) => m.key)).toEqual(["markets"]);
  });

  it("shows a cyber read when there is a CVE, a KEV listing or a CVSS score", () => {
    expect(lensMarkers(item({ cve_ids: ["CVE-2026-1"] })).map((m) => m.key)).toEqual(["cyber"]);
    expect(lensMarkers(item({ kev_listed: true })).map((m) => m.key)).toEqual(["cyber"]);
    expect(lensMarkers(item({ cvss_score: 9.8 })).map((m) => m.key)).toEqual(["cyber"]);
  });

  it("shows nothing when no professional reading exists", () => {
    row(item());
    expect(lensMarkers(item())).toEqual([]);
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("names the read for a screen reader", () => {
    row(item({ tickers: ["TCS"], cve_ids: ["CVE-2026-2"] }));
    expect(screen.getByRole("img", { name: "Markets read" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Cyber read" })).toBeInTheDocument();
  });
});

describe("ChartRow — the lead", () => {
  it("shows the lead's image only when the story has one — never a placeholder", () => {
    const { container, rerender } = render(
      <ol>
        <ChartRow item={item()} lead />
      </ol>,
    );
    expect(container.querySelector("img")).toBeNull();
    rerender(
      <ol>
        <ChartRow item={item({ image_url: "https://x/y.jpg" })} lead />
      </ol>,
    );
    expect(container.querySelector("img")).toHaveAttribute("src", "https://x/y.jpg");
  });

  it("never shows an image on an ordinary row", () => {
    const { container } = row(item({ image_url: "https://x/y.jpg" }));
    expect(container.querySelector("img")).toBeNull();
  });

  it("prints the lead's summary, and only the lead's", () => {
    row(item({ summary: "The summary." }), { lead: true });
    expect(screen.getByText("The summary.")).toBeInTheDocument();
    row(item({ id: "e2", summary: "Not shown." }));
    expect(screen.queryByText("Not shown.")).toBeNull();
  });
});
