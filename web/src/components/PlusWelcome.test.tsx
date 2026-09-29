import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";

import { PlusWelcome } from "@/components/PlusWelcome";

const params = vi.hoisted(() => ({ current: new URLSearchParams() }));
vi.mock("next/navigation", () => ({ useSearchParams: () => params.current }));
vi.mock("@/lib/session", () => ({ useSession: () => null }));
vi.mock("@/lib/analytics", async (orig) => ({ ...(await orig<typeof import("@/lib/analytics")>()), track: vi.fn() }));
const fetchEvent = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()), fetchEvent }));

beforeEach(() => {
  fetchEvent.mockReset().mockResolvedValue({ id: "e1", title: "RBI holds the repo rate at 5.5%" });
});

describe("the Plus welcome — sharing the story just unlocked (04 P2-9)", () => {
  it("offers the story the reader paid on, under its own headline", async () => {
    params.current = new URLSearchParams("next=/story/e1?lens=markets");
    render(<PlusWelcome />);
    expect(await screen.findByText("RBI holds the repo rate at 5.5%")).toBeInTheDocument();
    expect(fetchEvent).toHaveBeenCalledWith("e1");
    expect(screen.getByRole("button", { name: "Share this story" })).toBeInTheDocument();
  });

  it("offers nothing to share when the reader did not come from a story", async () => {
    params.current = new URLSearchParams("next=/feed");
    render(<PlusWelcome />);
    await act(async () => {});
    expect(fetchEvent).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Share this story" })).toBeNull();
  });

  it("offers nothing rather than a share with no headline when the story cannot load", async () => {
    fetchEvent.mockRejectedValue(new Error("event failed: 404"));
    params.current = new URLSearchParams("next=/story/gone");
    render(<PlusWelcome />);
    await act(async () => {});
    expect(screen.queryByRole("button", { name: "Share this story" })).toBeNull();
  });
});
