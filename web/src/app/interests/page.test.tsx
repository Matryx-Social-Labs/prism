import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import InterestsPage from "@/app/interests/page";

const fetchRegions = vi.hoisted(() => vi.fn());
const fetchTaxonomy = vi.hoisted(() => vi.fn());
const fetchLenses = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("@/lib/api", () => ({ fetchRegions, fetchTaxonomy, fetchLenses }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
// @/lib/profile and @/components/ProfileEditor stay real: the localStorage
// round-trip through picksToInterests/interestsToPicks IS the thing under test.

const KEY = "prism.profile.v1";

// loadProfile() returns null for a stored object with no `lens`, so every
// fixture that is meant to be read back must carry one.
const SAVED = {
  lens: "markets",
  region: "IN",
  state: "IN-KL",
  interests: ["politics:elections"],
  languages: ["hi", "en"],
};

function stateSelect() {
  // Two selects on the page; the state one is the one that isn't the language adder.
  return screen
    .getAllByRole("combobox")
    .find((el) => el.getAttribute("aria-label") !== "Add a language")!;
}

function saved() {
  return JSON.parse(localStorage.getItem(KEY) ?? "null");
}

async function saveIt() {
  await userEvent.click(screen.getByRole("button", { name: /Save & rebuild my feed/ }));
}

// Everything the page pulls has landed — otherwise a click races the taxonomy.
async function settled() {
  // "Sport", not "Politics": a loaded profile renames that chip to "Politics · 1".
  await screen.findByRole("button", { name: "Sport" });
  await screen.findByRole("option", { name: "Karnataka" });
}

beforeEach(() => {
  fetchRegions.mockReset().mockResolvedValue([
    { code: "IN-KL", name: "Kerala", covered: true },
    { code: "IN-KA", name: "Karnataka", covered: false },
  ]);
  fetchTaxonomy.mockReset().mockResolvedValue([
    { slug: "politics", name: "Politics", subsectors: [{ slug: "elections", name: "Elections" }] },
    { slug: "sports", name: "Sport", subsectors: [] },
  ]);
  fetchLenses.mockReset().mockResolvedValue([]); // falls back to the built-in lens set
  router.push.mockReset();
});

describe("Interests — round-trip", () => {
  it("re-saves a stored profile unchanged", async () => {
    localStorage.setItem(KEY, JSON.stringify(SAVED));
    render(<InterestsPage />);
    await settled();

    // The reader sees their own state, not the placeholder.
    expect(stateSelect()).toHaveValue("IN-KL");
    // ...and their saved sector, already counted down to one subsector.
    expect(screen.getByRole("button", { name: "Politics · 1" })).toBeInTheDocument();

    await saveIt();

    expect(saved()).toEqual(SAVED);
    expect(router.push).toHaveBeenCalledWith("/feed");
  });

  it("starts from the defaults when nothing is stored", async () => {
    render(<InterestsPage />);
    await settled();
    await saveIt();

    expect(saved()).toEqual({
      lens: "reader",
      region: "IN",
      state: null,
      interests: [],
      languages: ["en"],
    });
  });
});

describe("Interests — editing", () => {
  it("persists a changed state, lens and interest", async () => {
    render(<InterestsPage />);
    await settled();

    await userEvent.selectOptions(stateSelect(), "IN-KA");
    await userEvent.click(screen.getByRole("button", { name: "Cybersecurity / GRC" }));
    await userEvent.click(screen.getByRole("button", { name: "Politics" }));
    await userEvent.click(await screen.findByRole("button", { name: "Elections" }));
    await saveIt();

    expect(saved()).toEqual({
      lens: "cyber",
      region: "IN",
      state: "IN-KA",
      interests: ["politics:elections"],
      languages: ["en"],
    });
  });

  it("does not save what the reader cancelled", async () => {
    render(<InterestsPage />);
    await settled();

    await userEvent.click(screen.getByRole("button", { name: "Politics" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(localStorage.getItem(KEY)).toBeNull();
    expect(router.push).toHaveBeenCalledWith("/feed");
  });
});

describe("Interests — languages", () => {
  async function addHindi() {
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Add a language" }), "hi");
  }

  it("saves the reader's preference order, not the order they added them in", async () => {
    render(<InterestsPage />);
    await settled();
    await addHindi();

    // English is primary until Hindi is promoted over it.
    expect(saved()).toBeNull();
    await userEvent.click(screen.getAllByRole("button", { name: "Move up" })[1]);
    await saveIt();

    expect(saved().languages).toEqual(["hi", "en"]);
  });

  it("will not let the reader delete their primary language", async () => {
    render(<InterestsPage />);
    await settled();
    await addHindi();

    expect(screen.queryByRole("button", { name: "Remove en" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remove hi" }));
    await saveIt();

    expect(saved().languages).toEqual(["en"]);
  });
});

describe("Interests — when the regions API is down", () => {
  // The state dropdown is the only way to set a region, and fetchRegions() had
  // no .catch while useTaxonomy beside it did — so a down /api/v1/regions was an
  // unhandled rejection AND a silently empty dropdown.
  // Thin on purpose: the real guard is vitest itself. Without the .catch the
  // rejection is unhandled and the RUN exits 1 even though the assertions pass —
  // verified both ways. So CI fails on a regression here.
  it("does not take the page down when regions fail to load", async () => {
    fetchRegions.mockRejectedValue(new Error("offline"));
    render(<InterestsPage />);
    // The page still renders and the reader can still use the rest of it.
    expect(await screen.findByLabelText("Your state")).toBeInTheDocument();
  });

  it("gives the state dropdown an accessible name", async () => {
    render(<InterestsPage />);
    const select = await screen.findByLabelText("Your state");
    expect(select.tagName).toBe("SELECT");
  });
});
