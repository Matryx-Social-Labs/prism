import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import SourcesPage from "@/app/sources/page";
import type { MonitoredFeed } from "@/lib/api";

const fetchSources = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchSources }));

const ago = (min: number) => new Date(Date.now() - min * 60_000).toISOString();
const feed = (slug: string, over: Partial<MonitoredFeed> = {}): MonitoredFeed => ({
  slug, name: slug, publisher: slug, code: slug.slice(0, 2).toUpperCase(), origin: "national", language: "en", state: null, sector: null,
  domain: null, official: false, checked_at: ago(3), ok_at: ago(3), reachable: true, ...over,
});

beforeEach(() => fetchSources.mockReset());

describe("/sources — the monitored set, in public", () => {
  it("lists every outlet by origin, in the coverage bar's order, and says when each was last read", async () => {
    fetchSources.mockResolvedValue({
      outlets: 3, checked_at: ago(3),
      feeds: [
        feed("Prajavani", { language: "kn", origin: "regional", state: "IN-KA" }),
        feed("The Hindu"),
        feed("The Hindu Kerala", { publisher: "The Hindu", state: "IN-KL" }),
        feed("BBC Hindi", { language: "hi", origin: "regional", reachable: false, checked_at: ago(200), ok_at: ago(3000) }),
      ],
    });
    render(await SourcesPage());
    const heads = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
    expect(heads.slice(0, 4)).toEqual(["English national", "International", "Indian-language", "Wire / agency"]);
    // The denominator the story pages print is this page's own count.
    expect(document.body.textContent).toMatch(/2 of 3 monitored outlets/);
    expect(screen.getByText(/3 outlets · 4 feeds · 3 languages · checked 3m ago/)).toBeInTheDocument();
    expect(screen.getByText("Kerala desk")).toBeInTheDocument();
    // Two feeds from one masthead count once; an origin with none says so.
    const national = screen.getByRole("heading", { name: "English national" }).closest("section")!;
    expect(national.textContent).toMatch(/1 outlet · 2 feeds/);
    expect(within(screen.getByRole("heading", { name: "International" }).closest("section")!).getByText("None read yet.")).toBeInTheDocument();
    const indian = screen.getByRole("heading", { name: "Indian-language" }).closest("section")!;
    expect(within(indian).getByText(/Not reached since 2d ago/)).toBeInTheDocument();
    expect(within(indian).getByText("KN")).toBeInTheDocument();
  });

  it("names the most-read Indian languages it does not read yet", async () => {
    fetchSources.mockResolvedValue({ outlets: 1, checked_at: ago(1), feeds: [feed("a"), feed("b", { language: "hi" })] });
    render(await SourcesPage());
    const gaps = screen.getByRole("heading", { name: "Not read yet" }).closest("section")!;
    expect(gaps.textContent).toMatch(/Malayalam/);
    expect(gaps.textContent).not.toMatch(/Hindi/);
  });

  it("says so when the list cannot be reached, never an empty page", async () => {
    fetchSources.mockResolvedValue(null);
    render(await SourcesPage());
    expect(screen.getByText(/cannot be reached right now/)).toBeInTheDocument();
  });
});
