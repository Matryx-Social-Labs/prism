import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Suspense } from "react";
import LearnTask from "@/app/label/learn/[kind]/page";

const router = vi.hoisted(() => ({ push: vi.fn() }));
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
vi.mock("next/navigation", () => ({ useRouter: () => router, notFound }));

async function renderKind(kind: string) {
  await act(async () => {
    render(<Suspense fallback={null}><LearnTask params={Promise.resolve({ kind })} /></Suspense>);
  });
}

beforeEach(() => {
  router.push.mockReset();
  notFound.mockClear();
});

describe("learning a task before labelling it", () => {
  it("teaches the same-happening task with its real disagreements", async () => {
    await renderKind("event_identity");
    expect(screen.getByRole("heading", { name: "Is this the same happening?" })).toBeInTheDocument();
    expect(screen.getByText(/Do not tick the/)).toBeInTheDocument();
  });

  it("counts a late report of the same incident as the same happening", async () => {
    // The founder's correction, 2026-09-23: most candidates in the cross-language
    // batch are dated a day or more after their seed, and "the same day" told a
    // labeller to reject every one of them.
    await renderKind("event_identity");
    const page = document.body.textContent ?? "";
    expect(page).toMatch(/When it was reported does not matter/);
    expect(page).toMatch(/Tick a late report/);
    expect(page).not.toMatch(/same day|a day apart/i);
    // The one invented example says so, as every written example must.
    expect(screen.getByText("ILLUSTRATION")).toBeInTheDocument();
  });

  it("shows the claim task's worked examples opened, not collapsed", async () => {
    await renderKind("claim_attribution");
    expect(screen.getByText("NO — RIGHT QUOTE, WRONG MOUTH")).toBeVisible();
  });

  it("offers the way back to the workspace instead of starting a batch that is not there", async () => {
    await renderKind("story_boundary");
    await userEvent.click(screen.getByRole("button", { name: "Back to your workspace" }));
    expect(router.push).toHaveBeenCalledWith("/label");
  });

  it("teaches the quote-rendering task, the hard case included", async () => {
    await renderKind("quote_rendering");
    expect(screen.getByRole("heading", { name: "Same statement, or a translation?" })).toBeInTheDocument();
    expect(screen.getByText(/the same paper quoting the Prime Minister translates them/)).toBeInTheDocument();
  });

  it("is a 404 for a kind that has no guide", async () => {
    await expect(renderKind("nonsense")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });
});
