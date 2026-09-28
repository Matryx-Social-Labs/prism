import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HeaderNav } from "@/components/HeaderNav";

const mockPathname = vi.fn<() => string>();
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname(), useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/session", () => ({ useSession: () => null, usePlan: () => null }));

/**
 * The phone top bar on non-app pages (Claude Design · screens/PhoneBar.html, direction D):
 * lockup · spacer · one control. The theme toggle leaves the phone bar for the footer, and on
 * the landing the bar's button waits until the hero's own button has scrolled out, so no view
 * holds two primaries.
 */
let report: (visible: boolean) => void = () => {};
beforeEach(() => {
  // next/link observes too (prefetch), so bind to the observer that watches the hero's button.
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(private cb: IntersectionObserverCallback) {}
      observe(el: Element) {
        if (el.id !== "hero-cta") return;
        report = (visible) => this.cb([{ isIntersecting: visible } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
      }
      unobserve() {}
      disconnect() {}
      takeRecords() { return []; }
    },
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  document.getElementById("hero-cta")?.remove();
});

const cta = () => screen.getByRole("link", { name: /record/ });

describe("HeaderNav — the phone bar", () => {
  it("keeps the landing's button out of the phone bar until the hero's button scrolls away", () => {
    const hero = Object.assign(document.createElement("a"), { id: "hero-cta" });
    document.body.append(hero);
    mockPathname.mockReturnValue("/");
    render(<HeaderNav />);
    expect(cta()).toHaveClass("max-sm:invisible");
    act(() => report(false));
    expect(cta()).not.toHaveClass("max-sm:invisible");
    act(() => report(true));
    expect(cta()).toHaveClass("max-sm:invisible");
  });

  // The header stays mounted across routes, so arriving on the landing must reset the wait.
  it("starts hidden again when the reader comes back to the landing from another page", () => {
    const hero = Object.assign(document.createElement("a"), { id: "hero-cta" });
    document.body.append(hero);
    mockPathname.mockReturnValue("/about");
    const { rerender } = render(<HeaderNav />);
    expect(cta()).not.toHaveClass("max-sm:invisible");
    mockPathname.mockReturnValue("/");
    rerender(<HeaderNav />);
    expect(cta()).toHaveClass("max-sm:invisible");
  });

  it("always shows the button on /about, which has no hero button", () => {
    mockPathname.mockReturnValue("/about");
    render(<HeaderNav />);
    expect(cta()).not.toHaveClass("max-sm:invisible");
  });

  it("leaves the theme toggle out of the phone bar (it lives in the footer there)", () => {
    mockPathname.mockReturnValue("/plus");
    render(<HeaderNav />);
    expect(screen.getByRole("button", { name: /theme/ }).parentElement).toHaveClass("hidden", "sm:flex");
  });
});
