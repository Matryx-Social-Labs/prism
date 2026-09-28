import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { BackBar, StepIndicator, SystemPage, TextField } from "@/components/ui";

describe("SystemPage", () => {
  it("404 names what is missing and offers only today's record", () => {
    render(<SystemPage kind={404} />);
    expect(screen.getByRole("heading", { name: "Not in the record" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Today’s record" })).toHaveAttribute("href", "/feed");
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("an error prints its reference and retries", () => {
    const retry = vi.fn();
    render(<SystemPage kind="error" reference="abc123" onRetry={retry} />);
    expect(screen.getByText("500 · abc123")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});

describe("TextField", () => {
  it("an error replaces the hint and marks the field invalid", () => {
    render(<TextField label="Email" hint="We send a link" error="That address is missing its ending" value="r@x" onChange={() => {}} />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("That address is missing its ending");
    expect(screen.queryByText("We send a link")).toBeNull();
  });
});

describe("StepIndicator", () => {
  it("earlier steps can be revisited, later ones cannot", () => {
    const pick = vi.fn();
    render(<StepIndicator steps={["Where you are", "What you do", "What you follow"]} current={1} onPick={pick} />);
    fireEvent.click(screen.getByRole("button", { name: /Where you are/ }));
    expect(pick).toHaveBeenCalledWith(0);
    expect(screen.getByRole("button", { name: /What you follow/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /What you do/ })).toHaveAttribute("aria-current", "step");
  });
});

// The phone's back bars (founder pick B, 2026-09-28): an arrow that tells a screen reader
// where it goes, and the readPrism.news lockup centred, so a screenshot of any page under a
// back bar carries the brand.
describe("BackBar", () => {
  it("is an arrow back, named for where it goes, with the lockup centred", () => {
    render(<BackBar label="Today" href="/feed" />);
    const back = screen.getByRole("link", { name: "Back to Today" });
    expect(back).toHaveAttribute("href", "/feed");
    expect(back).not.toHaveTextContent("Today");
    expect(screen.getByRole("link", { name: "readPrism.news" })).toHaveAttribute("href", "/");
  });

  it("keeps the lockup when the page puts its own control on the right", () => {
    render(<BackBar label="Story" onBack={() => {}} right={<button type="button">Share</button>} />);
    expect(screen.getByRole("button", { name: "Back to Story" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "readPrism.news" })).toBeInTheDocument();
  });
});
