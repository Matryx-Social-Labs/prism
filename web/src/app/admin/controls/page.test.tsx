import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ControlsPage from "@/app/admin/controls/page";

const fetchFlags = vi.hoisted(() => vi.fn());
const triggerCollection = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchFlags, triggerCollection }));

const flags = (collecting: boolean) => ({
  seen_by: "api",
  flags: [
    { name: "PRISM_INGESTION_ENABLED", value: collecting, does: "Collect new reports" },
    { name: "PRISM_HEADLINE_TIER_THRESHOLD", value: 0, does: "Match stories across languages by headline (0: off)" },
  ],
});

beforeEach(() => {
  fetchFlags.mockReset().mockResolvedValue(flags(true));
  triggerCollection.mockReset().mockResolvedValue({ status: "ok", collecting: true });
  vi.stubGlobal("confirm", vi.fn(() => true));
});
afterEach(() => vi.unstubAllGlobals());

describe("controls", () => {
  it("shows every switch as a word or a number, never as a control", async () => {
    render(<ControlsPage />);
    expect(await screen.findByText("Collect new reports")).toBeInTheDocument();
    expect(screen.getByText("ON")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("asks before collecting, and does nothing if the founder backs out", async () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<ControlsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Collect now" }));
    expect(triggerCollection).not.toHaveBeenCalled();
  });

  it("says so when collection is switched off, rather than promising a run", async () => {
    fetchFlags.mockResolvedValue(flags(false));
    triggerCollection.mockResolvedValue({ status: "ok", collecting: false });
    render(<ControlsPage />);
    await screen.findByText("OFF");
    await userEvent.click(screen.getByRole("button", { name: "Collect now" }));
    expect(await screen.findByText(/collection is switched off/)).toBeInTheDocument();
  });

  it("counts the switches that are on, and draws off on a dashed rule, numbers apart", async () => {
    fetchFlags.mockResolvedValue(flags(false));
    render(<ControlsPage />);
    expect(await screen.findByRole("heading", { name: "Switches · 0 of 1 on" })).toBeInTheDocument();
    expect(screen.getByText("OFF").style.border).toContain("dashed");
    const limits = within(screen.getByRole("heading", { name: "Limits" }).closest("section")!);
    expect(limits.getByText("Match stories across languages by headline (0: off)")).toBeInTheDocument();
  });
});
