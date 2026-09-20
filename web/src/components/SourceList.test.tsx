import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReportCard, ReportImages, indexSources } from "@/components/SourceList";
import type { SourceRef } from "@/lib/api";

const src = (id: string, over: Partial<SourceRef> = {}): SourceRef => ({
  article_id: id, source_name: "The Hindu", source_slug: "thehindu", code: "TH", origin: "national", language: "en", publisher: "thehindu", domain: "thehindu.com",
  url: `https://x.test/${id}`, title: `Report ${id}`, published_at: "2026-09-18T06:00:00Z", stance: null, funding: null, ...over,
});

describe("ReportImages — the outlets' photographs, only as credited link previews", () => {
  it("renders one tile per distinct image, each opening its report and naming the outlet on the tile", () => {
    render(<ReportImages sources={[src("a", { image_url: "https://img/1.jpg" }), src("b", { image_url: "https://img/1.jpg" }), src("c", { image_url: "https://img/2.jpg", source_name: "Mint", code: "MINT" }), src("d")]} />);
    const tiles = screen.getAllByRole("link");
    expect(tiles).toHaveLength(2); // the duplicate image and the report without one are skipped
    expect(tiles[0]).toHaveAttribute("href", "https://x.test/a");
    expect(tiles[0]).toHaveAttribute("target", "_blank");
    expect(screen.getByText("Photo: The Hindu")).toBeInTheDocument();
    expect(screen.getByText("Photo: Mint")).toBeInTheDocument();
    // the image itself says whose it is, for a screen reader and for us
    expect(screen.getByAltText("Photo from Mint")).toHaveAttribute("referrerpolicy", "no-referrer");
  });

  it("renders nothing when no report carries an image", () => {
    const { container } = render(<ReportImages sources={[src("a"), src("b")]} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("ReportCard", () => {
  it("shows the outlet, the time, the outlet's headline and [n], and badges a thumbnail with the outlet's icon", () => {
    const list = [src("a", { image_url: "https://img/1.jpg" })];
    render(<ReportCard source={list[0]} n={indexSources(list).get("a")} />);
    const card = screen.getByRole("link", { name: "The Hindu: Report a" });
    expect(card).toHaveAttribute("href", "https://x.test/a");
    expect(card.textContent).toMatch(/The Hindu/);
    expect(card.textContent).toMatch(/\[1\]/);
    expect(card.textContent).toMatch(/English national/);
    expect(screen.getByAltText("Photo from The Hindu")).toBeInTheDocument();
  });
});

describe("ReportImages — one photo per publisher first", () => {
  it("leads with each publisher's first photo before a second from the same one", async () => {
    const { ReportImages } = await import("@/components/SourceList");
    const { render, screen, within } = await import("@testing-library/react");
    const src = (id: string, publisher: string, name: string) => ({ article_id: id, source_name: name, source_slug: id, url: `https://x.example/${id}`, title: `T ${id}`, published_at: null, stance: null, funding: null, publisher, image_url: `https://img.example/${id}.jpg` }) as never;
    render(<ReportImages sources={[src("bbc-ta", "bbc", "BBC Tamil"), src("bbc-te", "bbc", "BBC Telugu"), src("hindu", "thehindu", "The Hindu"), src("bbc-bn", "bbc", "BBC Bengali")]} />);
    const tiles = within(screen.getByRole("list", { name: "Images from the reports" })).getAllByRole("link");
    expect(tiles.map((a) => a.getAttribute("aria-label")?.split(":")[0])).toEqual(["BBC Tamil", "The Hindu", "BBC Telugu", "BBC Bengali"]);
  });
});
