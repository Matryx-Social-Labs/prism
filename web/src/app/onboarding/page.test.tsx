import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OnboardingPage from "@/app/onboarding/page";

// Onboarding walks the reservation form in three steps. The fields are the
// same components /you renders; this pins the walk itself: nothing blocks
// reading, a profession pre-sets the subjects, and the profile that lands in
// localStorage is what the three steps collected.
const useSession = vi.hoisted(() => vi.fn());
const fetchLanguages = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const fetchTaxonomy = vi.hoisted(() => vi.fn());
const fetchProfessions = vi.hoisted(() => vi.fn());
const fetchLenses = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("@/lib/session", () => ({ useSession, fetchLanguages, setProfile: vi.fn() }));
vi.mock("@/lib/api", () => ({ fetchRegions, fetchTaxonomy, fetchProfessions, fetchLenses }));
vi.mock("next/navigation", () => ({ useRouter: () => router, useSearchParams: () => new URLSearchParams("") }));

const KEY = "prism.profile.v1";
const saved = () => JSON.parse(localStorage.getItem(KEY) ?? "null");

beforeEach(() => {
  localStorage.clear();
  useSession.mockReset().mockReturnValue(null);
  router.push.mockReset();
  fetchRegions.mockReset().mockResolvedValue([{ code: "IN-KL", name: "Kerala", covered: true }]);
  fetchTaxonomy.mockReset().mockResolvedValue([
    { slug: "finance", name: "Finance", subsectors: [{ slug: "markets", name: "Stock market" }] },
    { slug: "sports", name: "Sports", subsectors: [] },
  ]);
  fetchProfessions.mockReset().mockResolvedValue([
    { group: "Finance", options: [{ slug: "trader", label: "Trader", lens: "markets", interests: ["finance"] }] },
  ]);
  fetchLanguages.mockReset().mockResolvedValue({
    languages: [{ code: "en", name: "English", native: "English" }, { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" }],
    default: ["en"],
  });
  fetchLenses.mockReset().mockResolvedValue([]);
});

describe("Onboarding — three steps of the reservation form", () => {
  it("collects state, then profession, then subjects, and saves them as one profile", async () => {
    render(<OnboardingPage />);
    // The states arrive from /regions after mount: wait for the option, not just the select.
    await screen.findByRole("option", { name: "Kerala" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Your state" }), "IN-KL");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await userEvent.selectOptions(await screen.findByRole("combobox", { name: "Your profession" }), "trader");
    expect(screen.getByText(/Reads as/)).toHaveTextContent("Finance / Trader");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    // Pre-set from the profession, then narrowed to a beat and widened by a subject.
    expect(await screen.findByRole("button", { name: /Business & Markets/ })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "Stock market" }));
    await userEvent.click(screen.getByRole("button", { name: /^Sports/ }));
    await userEvent.click(screen.getByRole("button", { name: "Build my feed" }));

    expect(saved()).toEqual({ lens: "markets", region: "IN", state: "IN-KL", interests: ["finance:markets", "sports"], languages: ["en"] });
    expect(router.push).toHaveBeenCalledWith("/feed");
  });

  it("lets the reader skip from any step without saving anything", async () => {
    render(<OnboardingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Skip for now" }));
    expect(saved()).toBeNull();
    expect(router.push).toHaveBeenCalledWith("/feed");
  });
});
