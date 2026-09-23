import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import BatchesPage from "@/app/admin/batches/page";

const fetchBatches = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchBatches }));

const batch = (over: Record<string, unknown>) => ({
  key: "k", name: "B", kind: "event_identity", purpose: "work", open: true, listed: false, self_join: true,
  created_at: "2026-09-23T10:00:00Z", tasks: 10, gated: 10, answered_tasks: 0, responses: 0, people: 0, ...over,
});

beforeEach(() => {
  fetchBatches.mockReset().mockResolvedValue({
    batches: [batch({ key: "open-link", name: "Founder link" }), batch({ key: "listed", name: "On the dashboard", listed: true })],
  });
});

describe("batches", () => {
  it("says anyone with the link can join only when they can", async () => {
    render(<BatchesPage />);
    const link = within((await screen.findByText("Founder link")).closest("li")!);
    expect(link.getByText(/Anyone with the link can join/)).toBeInTheDocument();
    // A listed batch refuses anonymous joining (api/routes/label.join), whatever self_join says.
    const listed = within(screen.getByText("On the dashboard").closest("li")!);
    expect(listed.queryByText(/Anyone with the link can join/)).not.toBeInTheDocument();
  });
});
