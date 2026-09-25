import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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
    expect(await screen.findByRole("heading", { name: "This area is for Prism's founders" })).toBeInTheDocument();
    // Says who they are signed in as, and that nothing was shown.
    expect(screen.getByText("founder@example.test")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Prism" })).toHaveAttribute("href", "/");
    expect(screen.queryByText("Labeller list")).not.toBeInTheDocument();
  });

  it("treats an expired session as signed out, not as forbidden", async () => {
    useSession.mockReturnValue(SESSION);
    fetchAdminMe.mockRejectedValue(new AdminError(401, "missing or invalid session"));
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("says the API could not be reached, with a reference, and tries again when asked", async () => {
    useSession.mockReturnValue(SESSION);
    fetchAdminMe.mockRejectedValueOnce(new AdminError(503, "unavailable")).mockResolvedValueOnce({ email: "founder@example.test" });
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByRole("heading", { name: "Prism's API could not be reached" })).toBeInTheDocument();
    expect(screen.getByText(/ERROR REF · API-503 ·/)).toBeInTheDocument();
    expect(screen.queryByText("Labeller list")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Labeller list")).toBeInTheDocument();
    expect(fetchAdminMe).toHaveBeenCalledTimes(2);
  });

  it("opens for a founder, and names who is signed in", async () => {
    useSession.mockReturnValue(SESSION);
    fetchAdminMe.mockResolvedValue({ email: "founder@example.test" });
    render(<AdminShell>{secret()}</AdminShell>);
    expect(await screen.findByText("Labeller list")).toBeInTheDocument();
    // The email sits in the phone bar and the sidebar; CSS shows one.
    expect(screen.getAllByText("founder@example.test").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });
});
