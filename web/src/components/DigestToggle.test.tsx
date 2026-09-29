import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// The week's record by email is consent (DPDP s.6): the box is unticked until
// the reader ticks it, its state is whatever the API saved (never assumed), and
// a failed save leaves the box as it was, saying so in words.
const fetchWeeklyDigest = vi.hoisted(() => vi.fn());
const setWeeklyDigest = vi.hoisted(() => vi.fn());
vi.mock("@/lib/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/session")>("@/lib/session");
  return { ...actual, fetchWeeklyDigest, setWeeklyDigest };
});

import { DigestToggle } from "@/components/DigestToggle";

const session = { userId: "u1", email: "reader@example.com" };
const LABEL = /The week’s record by email, Sunday morning \(IST\)/;

beforeEach(() => {
  fetchWeeklyDigest.mockReset().mockResolvedValue(false);
  setWeeklyDigest.mockReset().mockImplementation(async (_s, on: boolean) => on);
});
afterEach(() => {
  window.location.hash = "";
});

describe("DigestToggle", () => {
  it("starts unticked and shows no box until the saved state is known", async () => {
    let answer: (v: boolean) => void = () => {};
    fetchWeeklyDigest.mockReturnValue(new Promise<boolean>((r) => (answer = r)));
    render(<DigestToggle session={session} />);
    expect(screen.queryByRole("checkbox")).toBeNull();
    answer(false);
    expect(await screen.findByRole("checkbox", { name: LABEL })).not.toBeChecked();
    expect(setWeeklyDigest).not.toHaveBeenCalled();
  });

  it("ticking saves the consent, unticking withdraws it", async () => {
    render(<DigestToggle session={session} />);
    const box = await screen.findByRole("checkbox", { name: LABEL });
    await userEvent.click(box);
    await waitFor(() => expect(box).toBeChecked());
    expect(setWeeklyDigest).toHaveBeenLastCalledWith(session, true);
    await userEvent.click(box);
    await waitFor(() => expect(box).not.toBeChecked());
    expect(setWeeklyDigest).toHaveBeenLastCalledWith(session, false);
  });

  it("a failed save leaves the box as it was and says so", async () => {
    setWeeklyDigest.mockRejectedValue(new Error("500"));
    render(<DigestToggle session={session} />);
    const box = await screen.findByRole("checkbox", { name: LABEL });
    await userEvent.click(box);
    expect(await screen.findByText("That did not save. Try again.")).toBeInTheDocument();
    expect(box).not.toBeChecked();
  });

  it("a state that cannot load offers no box to tick from a guess", async () => {
    fetchWeeklyDigest.mockRejectedValue(new Error("500"));
    render(<DigestToggle session={session} />);
    expect(await screen.findByText(/could not load/)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("arriving at #digest lands on the box", async () => {
    window.location.hash = "#digest";
    render(<DigestToggle session={session} />);
    const box = await screen.findByRole("checkbox", { name: LABEL });
    await waitFor(() => expect(box).toHaveFocus());
    expect(box).not.toBeChecked();
  });
});
