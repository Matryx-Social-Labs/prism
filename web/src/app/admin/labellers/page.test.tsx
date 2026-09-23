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
  vi.stubGlobal("confirm", vi.fn(() => true));
});

describe("the labellers page", () => {
  it("approves an applicant and re-reads the list", async () => {
    render(<LabellersPage />);
    expect(await screen.findByText("“I read Kannada news daily”")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(setLabellerStatus).toHaveBeenCalledWith(expect.anything(), "new@example.test", "active");
    expect(fetchLabellers).toHaveBeenCalledTimes(2);
  });

  it("asks before removing someone, and does nothing if the founder backs out", async () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<LabellersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    expect(window.confirm).toHaveBeenCalled();
    expect(setLabellerStatus).not.toHaveBeenCalled();
  });

  it("prints a grant as a grant, with the live check count", async () => {
    render(<LabellersPage />);
    expect(await screen.findByText(/GRANTED BY f@example.test/)).toHaveTextContent("CHECKS 9/10");
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
    const form = (await screen.findByRole("heading", { name: "Add a labeller" })).closest("section")!;
    await userEvent.type(within(form).getByLabelText("Their account email"), "friend@example.test");
    await userEvent.click(within(form).getByRole("checkbox", { name: "Hindi" }));
    await userEvent.click(within(form).getByRole("button", { name: "Add labeller" }));
    expect(addLabeller).toHaveBeenCalledWith(expect.anything(), "friend@example.test", ["en", "hi"]);
  });
});
