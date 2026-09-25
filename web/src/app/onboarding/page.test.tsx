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
const setProfile = vi.hoisted(() => vi.fn());

vi.mock("@/lib/session", () => ({ useSession, fetchLanguages, setProfile }));
vi.mock("@/lib/api", () => ({ fetchRegions, fetchTaxonomy, fetchProfessions, fetchLenses }));
vi.mock("next/navigation", () => ({ useRouter: () => router, useSearchParams: () => new URLSearchParams("") }));

const KEY = "prism.profile.v1";
const saved = () => JSON.parse(localStorage.getItem(KEY) ?? "null");

beforeEach(() => {
  localStorage.clear();
  useSession.mockReset().mockReturnValue(null);
  router.push.mockReset();
  setProfile.mockReset().mockResolvedValue(undefined);
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
    // Covered states arrive from /regions after mount, as chips.
    await userEvent.click(await screen.findByRole("button", { name: "Kerala" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await screen.findByRole("option", { name: "Trader" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Profession" }), "trader");
    expect(screen.getByText(/Reads as/)).toHaveTextContent("Reads as Markets");
    expect(screen.getByText(/ticked for you in the next step/)).toHaveTextContent("Business & Markets is ticked for you in the next step.");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    // Pre-set from the profession, then narrowed to a beat and widened by a subject.
    const biz = await screen.findByRole("switch", { name: /Business & Markets/ });
    expect(biz).toHaveAttribute("aria-checked", "true");
    expect(biz).toHaveTextContent("Pre-set from your profession");
    await userEvent.click(screen.getByRole("button", { name: "Stock market" }));
    await userEvent.click(screen.getByRole("switch", { name: /^Sports/ }));
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

  it("goes back to an earlier step from the indicator, keeping the answer", async () => {
    render(<OnboardingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Kerala" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await userEvent.click(screen.getByRole("button", { name: /Where you are/ }));
    expect(screen.getByRole("button", { name: "Kerala" })).toHaveAttribute("aria-pressed", "true");
  });

  // Signed in, the account is saved too. When that fails the reader stays with
  // their answers and a way on — the old code swallowed the failure silently.
  it("keeps the answers and says so when the account could not be saved, then saves on a retry", async () => {
    useSession.mockReturnValue({ userId: "u", email: "asha@example.in" });
    setProfile.mockRejectedValueOnce(new Error("down"));
    render(<OnboardingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Continue" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Your name" }), "Asha");
    await screen.findByRole("option", { name: "Trader" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Profession" }), "trader");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("button", { name: "Build my feed" })).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Build my feed" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Your account could not be saved");
    expect(router.push).not.toHaveBeenCalled();
    expect(saved()?.lens).toBe("markets");

    await userEvent.click(screen.getByRole("button", { name: "Build my feed" }));
    expect(setProfile).toHaveBeenLastCalledWith(expect.anything(), { name: "Asha", profession: "trader", state: null, languages: ["en"], consent: true });
    expect(router.push).toHaveBeenCalledWith("/feed");
  });
});
