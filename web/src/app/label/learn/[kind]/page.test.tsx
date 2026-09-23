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

  it("shows the claim task's worked examples opened, not collapsed", async () => {
    await renderKind("claim_attribution");
    expect(screen.getByText("NO — RIGHT QUOTE, WRONG MOUTH")).toBeVisible();
  });

  it("offers the way back to the workspace instead of starting a batch that is not there", async () => {
    await renderKind("story_boundary");
    await userEvent.click(screen.getByRole("button", { name: "Back to your workspace" }));
    expect(router.push).toHaveBeenCalledWith("/label");
  });

  it("is a 404 for a kind that has no guide", async () => {
    await expect(renderKind("nonsense")).rejects.toThrow("NEXT_NOT_FOUND");
    expect(notFound).toHaveBeenCalled();
  });
});
