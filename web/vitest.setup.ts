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
vi.stubGlobal("ResizeObserver", MockResizeObserver);

// jsdom's scrollTo is a no-op that warns; make it actually move scrollY so the
// hook's "did the position stick?" check exercises real logic.
vi.stubGlobal("scrollTo", (x: number | ScrollToOptions, y?: number) => {
  const top = typeof x === "number" ? y ?? 0 : x?.top ?? 0;
  Object.defineProperty(window, "scrollY", { value: top, writable: true, configurable: true });
  window.dispatchEvent(new Event("scroll"));
});

afterEach(() => {
  cleanup();
  resizeObservers.length = 0;
  Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });
  sessionStorage.clear();
  vi.restoreAllMocks();
});
