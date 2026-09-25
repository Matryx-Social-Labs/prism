import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import LabellersPage from "@/app/admin/labellers/page";

const fetchLabellers = vi.hoisted(() => vi.fn());
const setLabellerStatus = vi.hoisted(() => vi.fn());
const setQualification = vi.hoisted(() => vi.fn());
const addLabeller = vi.hoisted(() => vi.fn());

// One object for the whole test, as the real shell's session is: a new one per
// render would re-run every page load and wipe unsaved edits.
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({
  ...(await orig<typeof import("@/components/admin/AdminShell")>()),
  useAdmin: () => ADMIN,
}));
vi.mock("@/lib/admin", async (orig) => ({
  ...(await orig<typeof import("@/lib/admin")>()),
  fetchLabellers,
  setLabellerStatus,
  setQualification,
  addLabeller,
}));

const person = (email: string, status: string, extra = {}) => ({
  email,
  name: null,
  status,
  languages_read: ["en", "kn"],
  note: null,
  created_at: "2026-09-23T10:00:00Z",
  approved_at: null,
  approved_by: null,
  answers: 3,
  last_answer_at: null,
  ...extra,
});

beforeEach(() => {
  fetchLabellers.mockReset().mockResolvedValue({
    labellers: [person("new@example.test", "applied", { note: "I read Kannada news daily" }), person("on@example.test", "active")],
    board: [{ email: "on@example.test", status: "active", kind: "event_identity", passed: true, best_score: null, attempts: 0, granted_by: "f@example.test", checks_right: 9, checks_total: 10 }],
    languages: ["en", "kn", "hi"],
  });
  setLabellerStatus.mockReset().mockResolvedValue({});
  setQualification.mockReset().mockResolvedValue({});
  addLabeller.mockReset().mockResolvedValue({});
});

describe("the labellers page", () => {
  it("approves an applicant and re-reads the list", async () => {
    render(<LabellersPage />);
    expect(await screen.findByText("“I read Kannada news daily”")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(setLabellerStatus).toHaveBeenCalledWith(expect.anything(), "new@example.test", "active");
    expect(fetchLabellers).toHaveBeenCalledTimes(2);
  });

  it("asks in place before removing someone, and does nothing if the founder backs out", async () => {
    render(<LabellersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    const ask = within(screen.getByRole("group", { name: "Yes, remove" }));
    expect(ask.getByText(/Their 3 answers are kept, and every kind they qualified for is withdrawn/)).toBeInTheDocument();
    await userEvent.click(ask.getByRole("button", { name: "Keep" }));
    expect(setLabellerStatus).not.toHaveBeenCalled();
    expect(screen.queryByRole("group", { name: "Yes, remove" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remove" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, remove" }));
    expect(setLabellerStatus).toHaveBeenCalledWith(expect.anything(), "on@example.test", "removed");
  });

  it("prints a grant as a grant, with the live check count", async () => {
    render(<LabellersPage />);
    const card = within((await screen.findByText(/GRANTED BY f@example.test/)).closest("li")!);
    expect(card.getByText("Granted")).toBeInTheDocument();
    expect(card.getByText("Hidden checks right").parentElement).toHaveTextContent("9 of 10");
    await userEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    expect(setQualification).toHaveBeenCalledWith(expect.anything(), "on@example.test", "event_identity", false);
  });

  it("shows the server's refusal instead of pretending it worked", async () => {
    setLabellerStatus.mockRejectedValue(new Error("no Prism account with the email x"));
    render(<LabellersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no Prism account with the email x");
  });

  it("adds an account with the languages ticked", async () => {
    render(<LabellersPage />);
    const form = (await screen.findByRole("heading", { name: "Add a labeller" })).closest("form")!;
    await userEvent.type(within(form).getByLabelText("Account email"), "friend@example.test");
    await userEvent.click(within(form).getByRole("button", { name: "Hindi" }));
    expect(within(form).getByRole("button", { name: "Hindi" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(within(form).getByRole("button", { name: "Add" }));
    expect(addLabeller).toHaveBeenCalledWith(expect.anything(), "friend@example.test", ["en", "hi"]);
  });

  it("finds a labeller by email or name, and by status", async () => {
    fetchLabellers.mockResolvedValue({
      labellers: [person("asha@example.test", "active", { name: "Asha" }), person("ravi@example.test", "paused")],
      board: [],
      languages: ["en"],
    });
    render(<LabellersPage />);
    // The list, not the grant form's picker, which names every active labeller too.
    const list = async () => within((await screen.findByRole("heading", { name: /^Labellers ·/ })).closest("section")!);
    expect((await list()).getByText("asha@example.test")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /Paused/ }));
    expect(screen.getByRole("radio", { name: /Paused/ })).toHaveAttribute("aria-checked", "true");
    expect((await list()).queryByText("asha@example.test")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Labellers · 1 of 2" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /All/ }));
    await userEvent.type(screen.getByRole("searchbox"), "asha");
    expect((await list()).getByText("asha@example.test")).toBeInTheDocument();
    expect((await list()).queryByText("ravi@example.test")).not.toBeInTheDocument();
  });
});
