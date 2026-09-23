import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { AdminShell } from "@/components/admin/AdminShell";
import { AdminError } from "@/lib/admin";

const useSession = vi.hoisted(() => vi.fn());
const fetchAdminMe = vi.hoisted(() => vi.fn());

vi.mock("@/lib/session", () => ({ useSession, authHeader: () => ({}) }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchAdminMe }));
vi.mock("next/navigation", () => ({ usePathname: () => "/admin" }));

const SESSION = { token: "t", userId: "u", email: "founder@example.test" };
const secret = () => <p>Labeller list</p>;

beforeEach(() => {
  useSession.mockReset().mockReturnValue(null);
  fetchAdminMe.mockReset();
});

describe("the admin shell", () => {
  it("asks a stranger to sign in and shows them nothing else", async () => {
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/signin?next=/admin");
    expect(screen.queryByText("Labeller list")).not.toBeInTheDocument();
    expect(fetchAdminMe).not.toHaveBeenCalled();
  });

  it("tells a signed-in reader who is not a founder that this is not for them", async () => {
    useSession.mockReturnValue(SESSION);
    fetchAdminMe.mockRejectedValue(new AdminError(403, "not an admin"));
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByText("This area is for Prism's founders.")).toBeInTheDocument();
    expect(screen.queryByText("Labeller list")).not.toBeInTheDocument();
  });

  it("treats an expired session as signed out, not as forbidden", async () => {
    useSession.mockReturnValue(SESSION);
    fetchAdminMe.mockRejectedValue(new AdminError(401, "missing or invalid session"));
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("opens for a founder, and names who is signed in", async () => {
    useSession.mockReturnValue(SESSION);
    fetchAdminMe.mockResolvedValue({ email: "founder@example.test" });
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByText("Labeller list")).toBeInTheDocument();
    expect(screen.getByText("founder@example.test")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });
});
