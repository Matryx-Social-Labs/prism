import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouteMap } from "@/components/RouteMap";

const dev = (id: string, day: number, title: string, source_count = 3) => ({ id, title, sector: null, occurred_at: new Date(Date.UTC(2026, 7, 27 + day)).toISOString(), image_url: null, is_current: false, why: null, source_count });
const node = (id: string, parent_id: string | null, off_spine = false) => ({ id, parent_id, off_spine, depth: 0 });
const devs = [dev("r", 0, "Aspirants summoned", 31), dev("a", 1, "High command meets", 18), dev("b", 3, "Expansion postponed", 44), dev("c", 5, "Siddaramaiah will not contest", 26), dev("x", 1, "Deputy CM demand", 9), dev("s", 2, "BJP mocks", 4)];
const tree = { root_id: "r", nodes: [node("r", null), node("a", "r"), node("b", "a"), node("c", "b"), node("x", "a"), node("s", "r", true)], shape: { developments: 6, branches: 1, satellites: 1, max_depth: 3 } };

// jsdom's matchMedia answers false to every query, so the map renders its
// phone form (vertical) by default; `wide()` answers the width query true.
const wide = () => vi.spyOn(window, "matchMedia").mockImplementation(((q: string) => ({
  matches: q.includes("min-width"), media: q, onchange: null, addListener: () => {}, removeListener: () => {}, addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
})) as typeof window.matchMedia);
afterEach(() => vi.restoreAllMocks());

describe("RouteMap — the rail map", () => {
  it("on a phone, reads top to bottom: every station a labelled hit target, the one you are on marked, the branch named", () => {
    render(<RouteMap tree={tree} developments={devs} currentId="b" />);
    expect(screen.getByRole("button", { name: /Expansion postponed, 30 Aug, 44 sources/ })).toBeInTheDocument();
    expect(screen.getByText(/You are here/)).toBeInTheDocument();
    expect(screen.getByText(/A branch · 1 development$/)).toBeInTheDocument();
    expect(screen.getByText("Also reported, off the main line")).toBeInTheDocument();
    // the main line runs down the page
    expect(document.querySelector(".rm-main")!.getAttribute("d")).toMatch(/^M36 \d+ V\d+$/);
  });

  it("from 640px, reads left to right with the labels beneath the line", () => {
    wide();
    render(<RouteMap tree={tree} developments={devs} currentId="b" />);
    expect(screen.getByText("You are here")).toBeInTheDocument();
    expect(document.querySelector(".rm-main")!.getAttribute("d")).toMatch(/^M\d+ 100 H\d+$/);
  });

  it("opens a station's card on tap with its count and a way to its ticket; the current station links nowhere", async () => {
    render(<RouteMap tree={tree} developments={devs} currentId="b" />);
    await userEvent.click(screen.getByRole("button", { name: /Aspirants summoned/ }));
    const card = screen.getByRole("dialog", { name: "Aspirants summoned" });
    expect(card).toHaveTextContent("31");
    expect(screen.getByRole("link", { name: /Open the ticket/ })).toHaveAttribute("href", "/story/r");
    await userEvent.click(screen.getByRole("button", { name: /Expansion postponed/ }));
    expect(screen.getByText("This is the ticket you are on")).toBeInTheDocument();
  });

  it("in compact form shows only this station and its neighbours, without satellites", () => {
    const long = [...devs, dev("d", 7, "Set for 12 September", 14), dev("e", 9, "Sworn in", 20)];
    const t = { ...tree, nodes: [...tree.nodes, node("d", "c"), node("e", "d")] };
    render(<RouteMap tree={t} developments={long} currentId="r" compact />);
    expect(screen.getByRole("button", { name: /Aspirants summoned/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Expansion postponed/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Set for 12 September/ })).toBeNull();
    expect(screen.queryByText("Also reported, off the main line")).toBeNull();
  });
});
