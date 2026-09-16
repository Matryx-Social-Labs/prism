import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HeroLensDemo } from "@/components/HeroLensDemo";

describe("HeroLensDemo — the flip, demonstrated", () => {
  it("re-inks the reading when a lens is picked", async () => {
    render(<HeroLensDemo />);
    expect(screen.getByRole("tab", { name: "Reader" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/The patent office cleared/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Markets" }));
    expect(screen.getByRole("tab", { name: "Markets" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/Generics names/)).toBeInTheDocument();
  });

  it("flips to a locked lens and shows the unlock prompt instead of the reading — the paywall moment", async () => {
    render(<HeroLensDemo locked={["markets"]} />);
    await userEvent.click(screen.getByRole("tab", { name: "Markets lens, locked" }));
    expect(screen.getByRole("tab", { name: "Markets lens, locked" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByText(/Generics names/)).toBeNull();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/signin");
  });
});
