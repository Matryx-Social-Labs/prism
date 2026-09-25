import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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
    batches: [batch({ key: "open-link", name: "Founder link" }), batch({ key: "listed", name: "Listed batch", listed: true })],
  });
});

describe("batches", () => {
  it("says anyone with the link can join only when they can", async () => {
    render(<BatchesPage />);
    const link = within((await screen.findByText("Founder link")).closest("li")!);
    expect(link.getByText(/Anyone with the link can join/)).toBeInTheDocument();
    // A listed batch refuses anonymous joining (api/routes/label.join), whatever self_join says.
    const listed = within(screen.getByText("Listed batch").closest("li")!);
    expect(listed.queryByText(/Anyone with the link can join/)).not.toBeInTheDocument();
  });

  it("shows each batch's progress as a count, and filters by state and by name or key", async () => {
    fetchBatches.mockResolvedValue({
      batches: [
        batch({ key: "hi-2026", name: "Hindi pairs", answered_tasks: 3, gated: 6 }),
        batch({ key: "kn-2026", name: "Kannada pairs", open: false }),
      ],
    });
    render(<BatchesPage />);
    const hindi = within((await screen.findByText("Hindi pairs")).closest("li")!);
    expect(hindi.getByText("Tasks answered").parentElement).toHaveTextContent("3 of 10");
    expect(hindi.getByText("Tasks with a language gate").parentElement).toHaveTextContent("6 of 10");

    await userEvent.click(screen.getByRole("radio", { name: /Closed/ }));
    expect(screen.queryByText("Hindi pairs")).not.toBeInTheDocument();
    expect(screen.getByText("Kannada pairs")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Work · 1 of 2" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("radio", { name: /All/ }));
    await userEvent.type(screen.getByRole("searchbox"), "hi-20");
    expect(screen.getByText("Hindi pairs")).toBeInTheDocument();
    expect(screen.queryByText("Kannada pairs")).not.toBeInTheDocument();
  });
});
