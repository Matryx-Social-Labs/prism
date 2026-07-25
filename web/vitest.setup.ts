import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom ships no ResizeObserver, and useScrollRestore depends on one. Tests that
// need to drive it grab the instances out of this registry and fire them.
export const resizeObservers: Array<{ cb: ResizeObserverCallback; disconnected: boolean }> = [];

class MockResizeObserver implements ResizeObserver {
  private entry: { cb: ResizeObserverCallback; disconnected: boolean };
  constructor(cb: ResizeObserverCallback) {
    this.entry = { cb, disconnected: false };
    resizeObservers.push(this.entry);
  }
  observe() {}
  unobserve() {}
  disconnect() {
    this.entry.disconnected = true;
  }
}
// Plain assignment, not vi.stubGlobal: the afterEach below calls
// vi.unstubAllGlobals(), which would rip these setup-level fakes out too.
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = MockResizeObserver;

// jsdom's scrollTo is a no-op that warns; make it actually move scrollY so the
// hook's "did the position stick?" check exercises real logic.
// jsdom implements neither window.scrollTo nor Element.prototype.scrollTo. The
// element one is a no-op here (AskPanel just pins its transcript to the bottom);
// the window one below actually moves scrollY so useScrollRestore is exercised.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {};
}

(globalThis as unknown as { scrollTo: unknown }).scrollTo = (
  x: number | ScrollToOptions,
  y?: number
) => {
  const top = typeof x === "number" ? y ?? 0 : x?.top ?? 0;
  Object.defineProperty(window, "scrollY", { value: top, writable: true, configurable: true });
  window.dispatchEvent(new Event("scroll"));
};

afterEach(() => {
  cleanup();
  resizeObservers.length = 0;
  Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });
  vi.restoreAllMocks();
  // restoreAllMocks does NOT undo vi.stubGlobal. Without this, a test that stubs
  // a throwing sessionStorage leaks it into every test that runs after it — the
  // suite then passes or fails on file ordering.
  vi.unstubAllGlobals();
  sessionStorage.clear();
});
