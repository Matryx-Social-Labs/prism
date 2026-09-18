import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BottomTabBar } from "@/components/BottomTabBar";
import { SiteHeader } from "@/components/SiteHeader";

const mockPathname = vi.fn<() => string>();
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname() }));
// HeaderNav pulls in session/lens fetching; the header's own routing logic is
// what's under test here.
vi.mock("@/components/HeaderNav", () => ({ HeaderNav: () => <nav>header nav</nav> }));

function at(path: string) {
  mockPathname.mockReturnValue(path);
}

describe("BottomTabBar — where it shows", () => {
  it.each(["/feed", "/trending", "/pulse", "/search", "/you", "/sector/business", "/watchlist"])(
    "shows on %s",
    (path) => {
      at(path);
      const { container } = render(<BottomTabBar />);
      expect(container.querySelector("nav")).not.toBeNull();
    }
  );

  it.each([
    ["/story/abc", "story pins its own lens rail + Share/Ask in the thumb zone"],
    ["/", "the landing — a first visitor is not inside the app yet"],
    ["/about", "about"],
    ["/onboarding", "onboarding"],
    ["/signin", "auth"],
  ])("hides on %s (%s)", (path) => {
    at(path);
    const { container } = render(<BottomTabBar />);
    expect(container.firstChild).toBeNull();
  });

  it("does not match a route that merely starts with a tab's name", () => {
    at("/feedback");
    const { container } = render(<BottomTabBar />);
    expect(container.firstChild).toBeNull();
  });
});

describe("BottomTabBar — active tab", () => {
  // /trending is the URL; "Stories" is the reader's word for it (2026-09-18).
  it("marks the current tab", () => {
    at("/trending");
    render(<BottomTabBar />);
    expect(screen.getByRole("link", { name: /stories/i })).toHaveAttribute("aria-current", "page");
  });

  // Asserting only the positive case lets an over-matching isActive ship green
  // (`() => true` lights every tab and still passes). Pin the count and a sibling.
  it("marks exactly one tab, and leaves the others alone", () => {
    at("/trending");
    render(<BottomTabBar />);
    const current = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("aria-current") === "page");
    expect(current).toHaveLength(1);
    expect(screen.getByRole("link", { name: /today/i })).not.toHaveAttribute("aria-current");
  });

  // The chart is /feed, and a sector is the chart filtered (D5 revised, D6).
  it("keeps Today active across the chart's routes, and only there", () => {
    for (const path of ["/feed", "/sector/business"]) {
      at(path);
      const { unmount } = render(<BottomTabBar />);
      expect(screen.getByRole("link", { name: /today/i })).toHaveAttribute("aria-current", "page");
      unmount();
    }
    at("/trending");
    render(<BottomTabBar />);
    expect(screen.getByRole("link", { name: /today/i })).not.toHaveAttribute("aria-current");
  });

  it("keeps You active across the routes that fold into it", () => {
    for (const path of ["/you", "/account", "/interests"]) {
      at(path);
      const { unmount } = render(<BottomTabBar />);
      expect(screen.getByRole("link", { name: /you/i })).toHaveAttribute("aria-current", "page");
      unmount();
    }
  });

  // Pulse left the bar (five tabs is the ceiling); a markets reader reaches it
  // from Watchlist, so the Watchlist tab stays lit there.
  it("keeps Watchlist active on Pulse", () => {
    for (const path of ["/watchlist", "/pulse"]) {
      at(path);
      const { unmount } = render(<BottomTabBar />);
      expect(screen.getByRole("link", { name: /watchlist/i })).toHaveAttribute("aria-current", "page");
      expect(screen.getByRole("link", { name: /you/i })).not.toHaveAttribute("aria-current");
      unmount();
    }
  });

  it("marks a detail route's parent tab", () => {
    at("/trending/kerala-power-crisis");
    render(<BottomTabBar />);
    expect(screen.getByRole("link", { name: /stories/i })).toHaveAttribute("aria-current", "page");
  });
});

describe("SiteHeader — the double-header fix", () => {
  it("hides the brand header on mobile for app routes that carry their own", () => {
    at("/feed");
    const { container } = render(<SiteHeader />);
    // `hidden lg:block` — gone on phones, still there on desktop.
    expect(container.querySelector("header")?.className).toContain("hidden");
  });

  it("hides it on a story detail route too", () => {
    at("/story/abc");
    const { container } = render(<SiteHeader />);
    expect(container.querySelector("header")?.className).toContain("hidden");
  });

  it("keeps it on the landing, marketing and auth routes", () => {
    for (const path of ["/", "/about", "/signin"]) {
      at(path);
      const { container, unmount } = render(<SiteHeader />);
      expect(container.querySelector("header")?.className).not.toContain("hidden");
      unmount();
    }
  });
});
