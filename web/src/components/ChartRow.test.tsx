import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChartRow, lensMarkers, rowSubject } from "@/components/ChartRow";
import type { FeedItem, OutletRef } from "@/lib/api";

const outlet = (slug: string, origin: OutletRef["origin"], language = "en", publisher = slug): OutletRef => ({
  slug, publisher, name: slug.toUpperCase(), code: slug.slice(0, 2).toUpperCase(), origin, language,
});

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
    outlets: [outlet("th", "national"), outlet("ht", "national"), outlet("pv", "regional", "kn"), outlet("bbc", "intl")],
    ...over,
  } as FeedItem;
}

const row = (it: FeedItem, props: Partial<Parameters<typeof ChartRow>[0]> = {}) =>
  render(
    <ol>
      <ChartRow item={it} {...props} />
    </ol>,
  );

describe("ChartRow — the meta line", () => {
  // Subject or place · time since the last report · languages, in that order.
  // finance prints its six-subject group, not the pipeline's ten.
  it("prints the subject group, then the time, then the languages", () => {
    row(item());
    const meta = document.querySelector(".meta-line")!;
    const texts = [...meta.querySelectorAll("span, time")].map((s) => s.textContent).filter((t) => t && t.trim());
    expect(texts[0]).toBe("Business & Markets");
    expect(meta.querySelector("time")).toHaveAttribute("dateTime", "2026-09-05T16:05:00Z");
    expect(texts.at(-1)).toBe("EN·KN");
  });

  it("omits the subject the page is already filtered to", () => {
    row(item(), { pageCode: "BIZ" });
    expect(screen.queryByText("Business & Markets")).toBeNull();
  });

  it('names the place when a story has no subject — never "Other"', () => {
    expect(rowSubject(item({ sector: "other", regions: ["IN", "IN-KA"] }), null)).toBe("Karnataka");
    expect(rowSubject(item({ sector: null, regions: ["IN"] }), null)).toBe("India");
    row(item({ sector: "other", regions: ["IN"] }));
    expect(screen.queryByText(/other/i)).toBeNull();
  });

  it("tags a headline in a script the reader did not choose, and only then", () => {
    row(item({ headline_lang: "kn", outlets: [outlet("th", "national")] }), { primaryLang: "en" });
    expect(screen.getByText("ಕನ್ನಡ")).toBeInTheDocument();
    row(item({ id: "e2", headline_lang: "kn", outlets: [outlet("th", "national")] }), { primaryLang: "kn" });
    expect(screen.getAllByText("ಕನ್ನಡ")).toHaveLength(1);
  });
});

describe("ChartRow — the coverage bar is the row's weight", () => {
  it("draws one segment per outlet origin in the fixed slot order and prints the count", () => {
    const { container } = row(item());
    const segs = [...container.querySelectorAll(".covbar > i")].map((i) => i.className);
    expect(segs).toEqual(["cov-national", "cov-intl", "cov-regional"]);
    expect(screen.getByText("4 outlets · 2 languages")).toBeInTheDocument();
  });

  it("counts mastheads, not feeds — six Hindu state feeds are one outlet", () => {
    row(item({ outlets: [outlet("thehindu", "national"), outlet("thehindu_karnataka", "national", "en", "thehindu"), outlet("ndtv", "national")] }));
    expect(screen.getByText("2 outlets")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "THEHINDU, NDTV" })).toBeInTheDocument();
  });

  it("falls back to the source count when a row predates outlet data", () => {
    const { container } = row(item({ outlets: undefined, source_count: 6 }));
    expect(container.querySelectorAll(".covbar > i")).toHaveLength(1);
    expect(screen.getByText("6 outlets")).toBeInTheDocument();
  });

  it("sets a single-source story on a dashed card", () => {
    const { container } = row(item({ source_count: 1, outlets: [outlet("th", "national")] }));
    expect(container.querySelector("a")!.className).toContain("single");
    expect(screen.getByText("1 outlet")).toBeInTheDocument();
  });

  it("marks the row the reader last opened", () => {
    row(item(), { lastOpened: true });
    expect(screen.getByRole("link")).toHaveAttribute("aria-current", "true");
    expect(screen.getByLabelText("Read")).toBeInTheDocument();
  });
});

describe("ChartRow — a lens dot says a professional reading exists", () => {
  it("shows a markets read when the pipeline found a ticker or a catalyst", () => {
    expect(lensMarkers(item({ tickers: ["RELIANCE"] })).map((m) => m.key)).toEqual(["markets"]);
    expect(lensMarkers(item({ catalyst: "earnings" })).map((m) => m.key)).toEqual(["markets"]);
  });

  it("shows a cyber read when there is a CVE, a KEV listing or a CVSS score", () => {
    expect(lensMarkers(item({ cve_ids: ["CVE-2026-1"] })).map((m) => m.key)).toEqual(["cyber"]);
    expect(lensMarkers(item({ kev_listed: true })).map((m) => m.key)).toEqual(["cyber"]);
    expect(lensMarkers(item({ cvss_score: 9.8 })).map((m) => m.key)).toEqual(["cyber"]);
  });

  it("names the read in words, never colour alone", () => {
    row(item({ tickers: ["TCS"], cve_ids: ["CVE-2026-2"] }));
    expect(screen.getByText("Markets read")).toBeInTheDocument();
    expect(screen.getByText("Cyber read")).toBeInTheDocument();
    expect(lensMarkers(item())).toEqual([]);
  });
});

describe("ChartRow — the photograph, credited (founder, 2026-09-20)", () => {
  it("shows the report's image as a credited thumbnail: the outlet's icon on it, the alt says whose it is", () => {
    const outlet = { slug: "thehindu", publisher: "thehindu", name: "The Hindu", code: "TH", origin: "national", language: "en", domain: "thehindu.com" };
    const { container } = row(item({ image_url: "https://x/y.jpg", image_outlet: outlet }), { lead: true });
    const img = container.querySelector("figure img")!;
    expect(img).toHaveAttribute("src", "https://x/y.jpg");
    expect(img).toHaveAttribute("alt", "Photo: The Hindu");
    expect(img).toHaveAttribute("referrerpolicy", "no-referrer");
    expect(container.querySelector("figure [title='Photo: The Hindu']")).toBeInTheDocument();
  });

  it("a row without a picture keeps its shape: no figure, no empty box", () => {
    const { container } = row(item({ image_url: null }));
    expect(container.querySelector("figure")).toBeNull();
  });

  it("prints what changed on every row, larger on the lead", () => {
    row(item({ summary: "The summary." }), { lead: true });
    expect(screen.getByText("The summary.").className).toContain("text-[16px]");
    row(item({ id: "e2", summary: "Also shown." }));
    expect(screen.getByText("Also shown.").className).toContain("text-[14.5px]");
  });
});
