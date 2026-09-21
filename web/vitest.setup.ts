// The product's clock is IST (news datelines and billing dates alike), so the
// suite runs on it too: a date rendered from an instant is then the same on a
// laptop in Berlin, on CI in UTC, and in Bengaluru, and lib/dateline.istTag is
// silent as it is for a reader at home. Set before anything touches Date.
process.env.TZ = "Asia/Kolkata";

import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom ships no ResizeObserver, and useScrollRestore depends on one. Tests that
// need to drive it grab the instances out of this registry and fire them.
export const resizeObservers: Array<{ cb: ResizeObserverCallback; disconnected: boolean }> = [];

// Setup files run under the node environment too (scope.node.test.ts, where the
// SSR guards live — jsdom always defines window, so they're unreachable here).
// Every DOM shim below has nothing to shim there, and touching `window` at all
// would fail the file before it collects a test.
const DOM = typeof window !== "undefined";

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

// jsdom has neither. StoryView reads matchMedia to honour prefers-reduced-motion
// on the lens flip, and drives its section nav off an IntersectionObserver —
// without these the component throws on mount and every test of it is dead.
if (DOM && typeof window.matchMedia !== "function") {
  window.matchMedia = ((query: string) => ({
    matches: false, // tests run as though motion is allowed
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

class MockIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds: ReadonlyArray<number> = [];
  constructor(_cb: IntersectionObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}
(globalThis as unknown as { IntersectionObserver: unknown }).IntersectionObserver =
  MockIntersectionObserver;

// This jsdom build ships sessionStorage but NOT localStorage — window.localStorage
// exists as an object with no methods, so anything touching it (the profile, the
// session, the scope preference) would throw or silently no-op in tests rather
// than exercise the real code path. Give it a working implementation.
if (DOM && typeof window.localStorage?.setItem !== "function") {
  const store = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
      key: (i: number) => [...store.keys()][i] ?? null,
      get length() {
        return store.size;
      },
    },
  });
}

// jsdom implements neither window.scrollTo nor Element.prototype.scrollTo. The
// element one is a no-op here (AskPanel just pins its transcript to the bottom);
// the window one below actually moves scrollY so useScrollRestore is exercised.
if (DOM && !Element.prototype.scrollTo) {
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
  if (!DOM) return; // node environment: nothing rendered, nothing stored
  cleanup();
  resizeObservers.length = 0;
  Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });
  vi.restoreAllMocks();
  // restoreAllMocks does NOT undo vi.stubGlobal. Without this, a test that stubs
  // a throwing sessionStorage leaks it into every test that runs after it — the
  // suite then passes or fails on file ordering.
  vi.unstubAllGlobals();
  sessionStorage.clear();
  // localStorage too, and for the same reason. The scope preference, profile and
  // session all live here now, and the Feed/Trending pages READ them on mount —
  // so one test's saved scope leaked into the next file and the suite passed or
  // failed on execution order. Caught with `vitest run --sequence.shuffle.tests`,
  // which is the only way this class of bug shows up.
  localStorage.clear();
});
