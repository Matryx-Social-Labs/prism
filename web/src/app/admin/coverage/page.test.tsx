import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import CoveragePage from "@/app/admin/coverage/page";
import { languageColours } from "@/components/admin/coverage/colours";

const fetchCoverage = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchCoverage }));
// WebGL does not exist in jsdom; the stub says what it was handed.
vi.mock("@/components/admin/coverage/CoverageGraph", () => ({
  default: ({ outlets }: { outlets: Array<{ name: string; color: string }> }) => (
    <p>3D: {outlets.map((o) => `${o.name} ${o.color}`).join(", ")}</p>
  ),
}));

const net = {
  range: { start: "2026-08-28", end: "2026-09-24" },
  source: "event_memberships · raw_items · sources",
  outlets: [
    { id: "a", name: "The Hindu", language: "en", country: "IN", stories: 40, shared: 30 },
    { id: "h", name: "Dainik Jagran", language: "hi", country: "IN", stories: 12, shared: 3 },
    { id: "z", name: "Lone Weekly", language: "en", country: "IN", stories: 2, shared: 0 },
  ],
  links: [{ a: "a", b: "h", shared: 3 }],
  languages: [{ a: "en", b: "hi", stories: 3 }],
  per_language: [{ language: "en", stories: 40 }, { language: "hi", stories: 12 }],
};

beforeEach(() => {
  fetchCoverage.mockReset().mockResolvedValue(net);
});
afterEach(() => vi.restoreAllMocks());

describe("the coverage page", () => {
  it("puts every number in a table before any 3D", async () => {
    render(<CoveragePage />);
    const pairs = within(await screen.findByRole("region", { name: "Stories in two languages" }));
    const pair = within(pairs.getByRole("row", { name: /English · Hindi/ }));
    // In both, then each language's own total.
    expect(pair.getAllByRole("cell").map((c) => c.textContent)).toEqual(["3", "40", "12"]);
    const outlets = within(screen.getByRole("region", { name: "Outlets" }));
    // Below thirty, a share is a count.
    expect(outlets.getByRole("row", { name: /Dainik Jagran/ })).toHaveTextContent("3 of 12");
    expect(outlets.getByRole("row", { name: /The Hindu/ })).toHaveTextContent("75%");
    expect(within(screen.getByRole("region", { name: "Strongest links" })).getByRole("row", { name: /The Hindu · Dainik Jagran/ })).toHaveTextContent("3");
    expect(screen.queryByText(/^3D:/)).not.toBeInTheDocument();
  });

  it("loads the 3D view only when asked, coloured by language, the unlinked left to the table", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as RenderingContext);
    render(<CoveragePage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open the 3D network" }));
    expect(await screen.findByText("3D: The Hindu var(--viz-1), Dainik Jagran var(--viz-2)")).toBeInTheDocument();
    expect(screen.getByText(/1 outlet with no shared story is left out/)).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Outlets" })).getByRole("row", { name: /Lone Weekly/ })).toBeInTheDocument();
  });

  it("says so in words when the browser cannot draw WebGL, and loads nothing", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    render(<CoveragePage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open the 3D network" }));
    expect(screen.getByText(/This browser can't draw the 3D network/)).toBeInTheDocument();
    expect(screen.queryByText(/^3D:/)).not.toBeInTheDocument();
  });

  it("on a day no story has two outlets, says so and counts the stories, still listing the outlets", async () => {
    fetchCoverage.mockResolvedValue({
      ...net,
      outlets: net.outlets.map((o) => ({ ...o, shared: 0 })),
      links: [],
      languages: [],
    });
    render(<CoveragePage />);
    expect(await screen.findByText("No story has two outlets yet")).toBeInTheDocument();
    expect(screen.getByText(/In this period: 52 stories, each from one outlet so far/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open the 3D network" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Outlets" })).toBeInTheDocument();
  });

  it("keeps the period last asked for when an earlier, slower answer lands after it", async () => {
    let answer90: (v: unknown) => void = () => {};
    fetchCoverage.mockImplementation((_s: unknown, days: number) =>
      days === 90 ? new Promise((r) => (answer90 = r)) : Promise.resolve({ ...net, outlets: [{ ...net.outlets[0], name: `Seven-day ${days}` }] }),
    );
    render(<CoveragePage />);
    await userEvent.click(await screen.findByRole("tab", { name: "90 days" }));
    await userEvent.click(screen.getByRole("tab", { name: "7 days" }));
    expect(await screen.findByText("Seven-day 7")).toBeInTheDocument();
    answer90({ ...net, outlets: [{ ...net.outlets[0], name: "Ninety-day" }] });
    await new Promise((r) => setTimeout(r, 0));
    expect(screen.queryByText("Ninety-day")).not.toBeInTheDocument();
    expect(screen.getByText("Seven-day 7")).toBeInTheDocument();
  });

  it("re-reads on a new period", async () => {
    render(<CoveragePage />);
    await userEvent.click(await screen.findByRole("tab", { name: "90 days" }));
    expect(fetchCoverage).toHaveBeenLastCalledWith(ADMIN.session, 90);
  });

  it("gives five languages their own colour and the rest one between them", () => {
    const langs = ["en", "hi", "kn", "ta", "te", "ml", "mr"].map((language, i) => ({ language, stories: 10 - i }));
    const { colour, key } = languageColours(langs);
    expect(colour("en")).toBe("var(--viz-1)");
    expect(colour("te")).toBe("var(--viz-5)");
    expect(colour("ml")).toBe(colour("mr"));
    expect(colour("ml")).toBe("var(--viz-6)");
    expect(key.map((k) => k.label).at(-1)).toBe("Other languages");
  });
});
