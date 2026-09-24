import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CorrectionsPage from "@/app/corrections/page";

const fetchCorrections = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchCorrections }));

beforeEach(() => fetchCorrections.mockReset());

describe("/corrections — the public log", () => {
  it("lists each correction with its record, reason and note, linking to the record's history", async () => {
    fetchCorrections.mockResolvedValue([{ event_id: "e1", title: "Bridge closes", created_at: "2026-09-24T06:00:00Z", reason: "source_correction", note: "The outlet corrected the toll from 14 to 12." }]);
    render(await CorrectionsPage());
    expect(screen.getByRole("link", { name: "Bridge closes" })).toHaveAttribute("href", "/story/e1#history");
    expect(screen.getByText(/The outlet corrected its report/)).toBeInTheDocument();
    expect(screen.getByText("The outlet corrected the toll from 14 to 12.")).toBeInTheDocument();
  });

  it("says there are none yet rather than showing an empty page, and says so when unreachable", async () => {
    fetchCorrections.mockResolvedValue([]);
    const { unmount } = render(await CorrectionsPage());
    expect(screen.getByText(/No corrections yet/)).toBeInTheDocument();
    unmount();
    fetchCorrections.mockResolvedValue(null);
    render(await CorrectionsPage());
    expect(screen.getByText(/cannot be reached right now/)).toBeInTheDocument();
  });
});
