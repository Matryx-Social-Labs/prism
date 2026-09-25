import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { StepIndicator, SystemPage, TextField } from "@/components/ui";

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
