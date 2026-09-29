import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// The landing's email line signs the visitor in and lands them on the account's
// unticked box (/account#digest). It must never subscribe anyone by itself.
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchFeed: vi.fn().mockResolvedValue([]), fetchSources: vi.fn().mockResolvedValue(null), fetchEvent: vi.fn(), fetchTrendingStory: vi.fn() };
});
vi.mock("@/lib/billing", async () => {
  const actual = await vi.importActual<typeof import("@/lib/billing")>("@/lib/billing");
  return { ...actual, fetchPlans: vi.fn().mockRejectedValue(new Error("no plans in this test")) };
});
vi.mock("@/lib/lenses", () => ({ useLenses: () => [] }));

import { Landing } from "@/components/Landing";

describe("Landing · the week's record by email", () => {
  it("goes through sign-in to the account's box, carrying the anchor", async () => {
    render(await Landing());
    const link = screen.getByRole("link", { name: "Get the week’s record by email" });
    expect(link).toHaveAttribute("href", "/signin?next=%2Faccount%23digest");
    expect(screen.getByText(/Nothing is sent until you turn it on/)).toBeInTheDocument();
  });
});
