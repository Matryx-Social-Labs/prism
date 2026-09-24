import { beforeEach, describe, expect, it, vi } from "vitest";
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
  ],
  links: [{ a: "a", b: "h", shared: 3 }],
  languages: [{ a: "en", b: "hi", stories: 3 }],
  per_language: [{ language: "en", stories: 40 }, { language: "hi", stories: 12 }],
};

beforeEach(() => {
  fetchCoverage.mockReset().mockResolvedValue(net);
});

describe("the coverage page", () => {
  it("puts every number in a table before any 3D", async () => {
    render(<CoveragePage />);
    const pairs = within(await screen.findByRole("region", { name: "Stories reported in two languages" }));
    expect(pairs.getByRole("row", { name: /English \+ Hindi/ })).toHaveTextContent("340 · 12");
    const outlets = within(screen.getByRole("region", { name: "Outlets" }));
    // Below thirty, a share is a count.
    expect(outlets.getByRole("row", { name: /Dainik Jagran/ })).toHaveTextContent("3 of 12");
    expect(outlets.getByRole("row", { name: /The Hindu/ })).toHaveTextContent("75%");
    expect(within(screen.getByRole("region", { name: "Strongest links" })).getByRole("row", { name: /The Hindu \+ Dainik Jagran/ })).toHaveTextContent("3");
    expect(screen.queryByText(/^3D:/)).not.toBeInTheDocument();
  });

  it("loads the 3D view only when asked, coloured by language", async () => {
    render(<CoveragePage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open the 3D view" }));
    expect(await screen.findByText("3D: The Hindu var(--viz-1), Dainik Jagran var(--viz-2)")).toBeInTheDocument();
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
