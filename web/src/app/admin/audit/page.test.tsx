import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AuditPage from "@/app/admin/audit/page";

const fetchAudit = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchAudit }));

const entry = (action: string, created_at: string, detail = {}) => ({ actor: "f@example.test", action, target: "tKECdZfjiL0n", detail, created_at });

beforeEach(() => {
  fetchAudit.mockReset().mockResolvedValue({
    entries: [
      // 00:30 IST on 24 Sep is still 23 Sep in UTC: grouped by the IST day.
      entry("batch.languages", "2026-09-23T19:00:00Z", { gated: { hi: 3 } }),
      entry("labeller.status", "2026-09-23T10:00:00Z", { status: "active" }),
      entry("batch.open", "2026-09-22T10:00:00Z"),
    ],
  });
});

describe("the audit timeline", () => {
  it("groups changes by IST day, in words, with the code and details kept", async () => {
    render(<AuditPage />);
    const first = within(await screen.findByRole("region", { name: "24 Sept" }));
    expect(first.getByText("1 CHANGE")).toBeInTheDocument();
    expect(first.getByText("Filled in a batch's languages")).toBeInTheDocument();
    expect(first.getByText(/batch\.languages · f@example\.test · gated \{"hi":3\}/)).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "23 Sept" })).getByText("Changed a labeller's status")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "22 Sept" })).toBeInTheDocument();
  });

  it("filters by area and counts each", async () => {
    render(<AuditPage />);
    await userEvent.click(await screen.findByRole("tab", { name: /Labellers/ }));
    expect(screen.queryByText("Filled in a batch's languages")).not.toBeInTheDocument();
    expect(screen.getByText("Changed a labeller's status")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Batches/ })).toHaveTextContent("2");
  });
});
