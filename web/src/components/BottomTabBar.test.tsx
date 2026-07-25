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
  it.each(["/feed", "/trending", "/pulse", "/search", "/you", "/sector/markets", "/watchlist"])(
    "shows on %s",
    (path) => {
      at(path);
      const { container } = render(<BottomTabBar />);
      expect(container.querySelector("nav")).not.toBeNull();
    }
  );

  it.each([
    ["/story/abc", "story pins its own lens rail + Share/Ask in the thumb zone"],
    ["/", "landing"],
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
  it("marks the current tab", () => {
    at("/trending");
    render(<BottomTabBar />);
    expect(screen.getByRole("link", { name: /trending/i })).toHaveAttribute("aria-current", "page");
  });

  it("keeps You active across the routes that fold into it", () => {
    for (const path of ["/you", "/account", "/interests", "/watchlist"]) {
      at(path);
      const { unmount } = render(<BottomTabBar />);
      expect(screen.getByRole("link", { name: /you/i })).toHaveAttribute("aria-current", "page");
      unmount();
    }
  });

  it("marks a detail route's parent tab", () => {
    at("/trending/kerala-power-crisis");
    render(<BottomTabBar />);
    expect(screen.getByRole("link", { name: /trending/i })).toHaveAttribute("aria-current", "page");
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

  it("keeps it on marketing and auth routes", () => {
    for (const path of ["/", "/about", "/signin"]) {
      at(path);
      const { container, unmount } = render(<SiteHeader />);
      expect(container.querySelector("header")?.className).not.toContain("hidden");
      unmount();
    }
  });
});
