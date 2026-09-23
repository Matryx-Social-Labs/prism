import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Suspense } from "react";

import LearnTask from "@/app/label/learn/[kind]/page";
import type { LabelGuide } from "@/lib/api";

const router = vi.hoisted(() => ({ push: vi.fn() }));
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
const useSession = vi.hoisted(() => vi.fn());
const fetchGuide = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => router, notFound }));
vi.mock("@/lib/session", () => ({ useSession, authHeader: () => ({}) }));
vi.mock("@/lib/labeller", async (orig) => ({ ...(await orig<typeof import("@/lib/labeller")>()), fetchGuide }));

const SESSION = { token: "t", userId: "u", email: "l@example.test" };

// A stand-in: the real words are served by the API and pinned in
// tests/test_label_guides.py. This pins what the page does with them.
const GUIDE: LabelGuide = {
  kind: "event_identity",
  question: "Is this the same happening?",
  minutes: 2,
  in_short: "Tick every report of the one incident, whatever day an outlet reported it.",
  lede: ["Tick the ones that report the **same incident**."],
  do: ["Tick a **late report** of it too."],
  dont: ["Do not tick the **follow-up**."],
  examples_label: "Examples",
  examples: [
    { mark: "yes", head: "TICK — a real pair", body: "One statement." },
    { mark: "yes", illustration: true, head: "TICK — an invented late report", body: "A day later." },
  ],
  start: "Start",
  after: null,
};

async function renderKind(kind: string) {
  await act(async () => {
    render(<Suspense fallback={null}><LearnTask params={Promise.resolve({ kind })} /></Suspense>);
  });
}

beforeEach(() => {
  router.push.mockReset();
  notFound.mockClear();
  useSession.mockReset().mockReturnValue(null);
  fetchGuide.mockReset().mockResolvedValue(GUIDE);
});

describe("learning a task, once you have applied", () => {
  it("asks a stranger to sign in, and never fetches the guide", async () => {
    await renderKind("event_identity");
    expect(await screen.findByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/signin?next=/label/learn/event_identity");
    expect(fetchGuide).not.toHaveBeenCalled();
    expect(screen.queryByText(/same incident/)).not.toBeInTheDocument();
  });

  it("sends a signed-in reader who has not applied to apply", async () => {
    useSession.mockReturnValue(SESSION);
    fetchGuide.mockRejectedValue(Object.assign(new Error("apply at /label to read the guides"), { status: 403 }));
    await renderKind("event_identity");
    expect(await screen.findByRole("link", { name: "Apply to label" })).toHaveAttribute("href", "/label");
    expect(screen.queryByText(/same incident/)).not.toBeInTheDocument();
  });

  it("teaches an applicant, In short first and the invented example marked", async () => {
    useSession.mockReturnValue(SESSION);
    await renderKind("event_identity");
    expect(await screen.findByRole("heading", { name: "Is this the same happening?" })).toBeInTheDocument();
    expect(fetchGuide).toHaveBeenCalledWith(SESSION, "event_identity");
    expect(screen.getByText(/whatever day an outlet reported it/)).toBeInTheDocument();
    // **markup** becomes emphasis, not literal asterisks.
    expect(screen.getByText("same incident").tagName).toBe("STRONG");
    expect(screen.getAllByText("ILLUSTRATION")).toHaveLength(1);
  });

  it("offers the way back to the workspace instead of starting a batch that is not there", async () => {
    useSession.mockReturnValue(SESSION);
    await renderKind("event_identity");
    await userEvent.click(await screen.findByRole("button", { name: "Back to your workspace" }));
    expect(router.push).toHaveBeenCalledWith("/label");
  });

  it("treats a kind with no guide as a page that does not exist", async () => {
    await expect(renderKind("made_up")).rejects.toThrow("NEXT_NOT_FOUND");
  });
});
