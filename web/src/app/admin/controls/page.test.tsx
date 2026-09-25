import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ControlsPage from "@/app/admin/controls/page";

const fetchFlags = vi.hoisted(() => vi.fn());
const triggerCollection = vi.hoisted(() => vi.fn());
const fetchAudit = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchFlags, triggerCollection, fetchAudit }));

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
  fetchAudit.mockReset().mockResolvedValue({ entries: [] });
});

describe("controls", () => {
  it("shows every switch as a word or a number, never as a control", async () => {
    render(<ControlsPage />);
    expect(await screen.findByText("Collect new reports")).toBeInTheDocument();
    expect(screen.getByText("ON")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("asks in place before collecting, and does nothing if the founder backs out", async () => {
    render(<ControlsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Collect now" }));
    expect(screen.getByText(/Ask the worker to collect new reports now\?/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(triggerCollection).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Collect now" })).toBeInTheDocument();
  });

  it("says when it asked and what it was recorded as", async () => {
    render(<ControlsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Collect now" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, collect" }));
    expect(triggerCollection).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/ASKED AT \d\d:\d\d IST · RECORDED AS pipeline\.run BY f@example\.test/)).toBeInTheDocument();
  });

  it("says so when collection is switched off, rather than promising a run", async () => {
    fetchFlags.mockResolvedValue(flags(false));
    triggerCollection.mockResolvedValue({ status: "ok", collecting: false });
    render(<ControlsPage />);
    await screen.findByText("OFF");
    await userEvent.click(screen.getByRole("button", { name: "Collect now" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, collect" }));
    expect(await screen.findByText("Collection is switched off")).toBeInTheDocument();
    expect(screen.queryByText(/ASKED AT/)).not.toBeInTheDocument();
  });

  it("counts the switches that are on, and draws off on a dashed rule, numbers apart", async () => {
    fetchFlags.mockResolvedValue(flags(false));
    render(<ControlsPage />);
    expect(await screen.findByRole("heading", { name: "Switches" })).toBeInTheDocument();
    expect(await screen.findByText(/^0 OF 1 ON/)).toBeInTheDocument();
    expect(screen.getByText("OFF").style.borderStyle).toBe("dashed");
    const limits = within(screen.getByRole("heading", { name: "Limits" }).closest("section")!);
    expect(limits.getByText("Match stories across languages by headline (0: off)")).toBeInTheDocument();
  });

  it("lists today's changes from the audit log, and says when it could not look", async () => {
    const now = new Date().toISOString();
    fetchAudit.mockResolvedValue({
      entries: [
        { actor: "f@example.test", action: "pipeline.run", target: "ingestion", detail: {}, created_at: now },
        { actor: "f@example.test", action: "batch.open", target: "old", detail: {}, created_at: "2020-01-01T10:00:00Z" },
      ],
    });
    const { unmount } = render(<ControlsPage />);
    expect(await screen.findByText("Asked the worker to collect")).toBeInTheDocument();
    expect(screen.getByText("1 CHANGE")).toBeInTheDocument();
    expect(screen.queryByText("Opened or closed a batch")).not.toBeInTheDocument();
    unmount();
    fetchAudit.mockRejectedValue(new Error("offline"));
    render(<ControlsPage />);
    expect(await screen.findByText(/Could not load today's changes/)).toBeInTheDocument();
    expect(screen.queryByText(/Nothing was changed/)).not.toBeInTheDocument();
  });
});
