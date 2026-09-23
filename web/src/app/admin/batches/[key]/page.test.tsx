import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import RoundReview from "@/app/admin/batches/[key]/page";

const fetchRound = vi.hoisted(() => vi.fn());
const saveExplanations = vi.hoisted(() => vi.fn());
const setOpen = vi.hoisted(() => vi.fn());

// One object for the whole test, as the real shell's session is: a new one per
// render would re-run every page load and wipe unsaved edits.
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({
  ...(await orig<typeof import("@/components/admin/AdminShell")>()),
  useAdmin: () => ADMIN,
}));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchRound, saveExplanations, setOpen }));

const check = (ok: boolean, reasons: string[] = []) => ({
  name: "Practice — claim_attribution",
  purpose: "practice",
  items: 2,
  missing: ok ? 0 : 1,
  scores: { "always yes": 0.5, "always no": 0.5 },
  ok,
  reasons,
});
const items = [
  { position: 0, speaker: "A. Speaker", quote: "We will build it", answer: "yes", explanation: "The article says so." },
  { position: 1, speaker: "B. Other", quote: "We will build it", answer: "no", explanation: "" },
];

beforeEach(() => {
  fetchRound.mockReset().mockResolvedValue({ items, check: check(false, ["1 item(s) have no explanation"]) });
  saveExplanations.mockReset().mockResolvedValue({ saved: 1, check: check(true) });
  setOpen.mockReset().mockResolvedValue({});
});

const page = () => render(<RoundReview params={Promise.resolve({ key: "k1" })} />);

describe("reviewing a round", () => {
  it("says why it cannot be published, and will not publish it", async () => {
    page();
    expect(await screen.findByText("1 item(s) have no explanation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled();
  });

  it("saves only the explanations that changed", async () => {
    page();
    const boxes = await screen.findAllByRole("textbox");
    await userEvent.type(boxes[1], "Only A. Speaker is credited in the article.");
    await userEvent.click(screen.getByRole("button", { name: /Save 1 change/ }));
    expect(saveExplanations).toHaveBeenCalledWith(expect.anything(), "k1", [
      { position: 1, explanation: "Only A. Speaker is credited in the article." },
    ]);
  });

  it("publishes once the check passes and nothing is unsaved", async () => {
    fetchRound.mockResolvedValue({ items, check: check(true) });
    page();
    const publish = await screen.findByRole("button", { name: "Publish" });
    expect(publish).toBeEnabled();
    await userEvent.click(publish);
    expect(setOpen).toHaveBeenCalledWith(expect.anything(), "k1", true);
    expect(await screen.findByText("Published: labellers can take it now")).toBeInTheDocument();
  });
});
