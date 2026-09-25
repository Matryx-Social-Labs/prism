import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const fetchVersions = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchVersions }));

import { RecordHistory } from "@/components/RecordHistory";

afterEach(() => fetchVersions.mockReset());

describe("RecordHistory — corrections always, versions on request", () => {
  it("prints each correction with its date and reason in words, and loads nothing until asked", () => {
    render(<RecordHistory eventId="e1" corrections={[{ created_at: "2026-09-24T06:00:00Z", reason: "prism_error", note: "The headline named the wrong district." }]} />);
    const list = screen.getByRole("list", { name: "Corrections" });
    expect(within(list).getByText("Corrected")).toBeInTheDocument();
    expect(within(list).getByText("24 Sept")).toHaveAttribute("dateTime", "2026-09-24T06:00:00Z");
    expect(within(list).getByText("Prism's error")).toBeInTheDocument();
    expect(screen.getByText("The headline named the wrong district.")).toBeInTheDocument();
    expect(fetchVersions).not.toHaveBeenCalled();
  });

  it("shows every earlier headline and free brief when asked", async () => {
    fetchVersions.mockResolvedValue({ corrections: [], versions: [{ replaced_at: "2026-09-23T06:00:00Z", title: "Old headline", summary: null, brief: "First point. Second point." }] });
    render(<RecordHistory eventId="e1" corrections={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Earlier versions of this record" }));
    expect(await screen.findByText("Old headline")).toBeInTheDocument();
    expect(screen.getByText("Second point.")).toBeInTheDocument();
    // The whole list is served, so each version carries its number, counted from the first.
    expect(within(screen.getByRole("list", { name: "Earlier versions" })).getByText("v1")).toBeInTheDocument();
    expect(fetchVersions).toHaveBeenCalledWith("e1");
  });

  it("says so when a record never changed", async () => {
    fetchVersions.mockResolvedValue({ corrections: [], versions: [] });
    render(<RecordHistory eventId="e1" corrections={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Earlier versions of this record" }));
    expect(await screen.findByText(/has not changed since it was first written/)).toBeInTheDocument();
  });
});
