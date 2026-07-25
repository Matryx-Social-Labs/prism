import React from "react";
import { describe, expect, it, vi } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";
import { useScrollRestore } from "@/lib/useScrollRestore";
import { resizeObservers } from "../../vitest.setup";

const KEY = "test:scrollY";

function scrollTo(y: number) {
  window.scrollTo(0, y);
}
// The saver is rAF-throttled; flush it.
async function flushSave() {
  await act(async () => {
    await new Promise((r) => requestAnimationFrame(() => r(null)));
  });
}
function growDocument() {
  act(() => {
    for (const o of resizeObservers) {
      if (!o.disconnected) o.cb([], {} as ResizeObserver);
    }
  });
}

describe("useScrollRestore — saving", () => {
  it("persists the reader's position as they scroll", async () => {
    renderHook(() => useScrollRestore(KEY, true));
    scrollTo(640);
    await flushSave();
    expect(sessionStorage.getItem(KEY)).toBe("640");
  });

  it("never persists 0 — the router scrolls the still-mounted list to top on nav away", async () => {
    sessionStorage.setItem(KEY, "640");
    renderHook(() => useScrollRestore(KEY, true));
    scrollTo(0);
    await flushSave();
    // A spurious 0 must not clobber the real position.
    expect(sessionStorage.getItem(KEY)).toBe("640");
  });

  it("does not let a mid-restore clamped position overwrite the target", async () => {
    sessionStorage.setItem(KEY, "900");
    renderHook(() => useScrollRestore(KEY, true));
    // Restore is in flight; a short page clamps scrollTo to 300.
    scrollTo(300);
    await flushSave();
    expect(sessionStorage.getItem(KEY)).toBe("900");
  });
});

describe("useScrollRestore — restoring", () => {
  it("does nothing until the list's data is ready", () => {
    sessionStorage.setItem(KEY, "500");
    renderHook(() => useScrollRestore(KEY, false));
    expect(window.scrollY).toBe(0);
  });

  it("restores once the data arrives", () => {
    sessionStorage.setItem(KEY, "500");
    const { rerender } = renderHook(({ ready }) => useScrollRestore(KEY, ready), {
      initialProps: { ready: false },
    });
    rerender({ ready: true });
    expect(window.scrollY).toBe(500);
  });

  it("re-asserts as late-loading images grow the document", () => {
    sessionStorage.setItem(KEY, "1200");
    renderHook(() => useScrollRestore(KEY, true));
    // Page was still short, so the browser clamped the restore.
    act(() => {
      Object.defineProperty(window, "scrollY", { value: 800, writable: true, configurable: true });
    });
    growDocument();
    expect(window.scrollY).toBe(1200);
  });

  it("stops fighting the reader the moment they scroll themselves", () => {
    sessionStorage.setItem(KEY, "1200");
    renderHook(() => useScrollRestore(KEY, true));
    act(() => {
      window.dispatchEvent(new Event("touchstart"));
    });
    act(() => {
      Object.defineProperty(window, "scrollY", { value: 300, writable: true, configurable: true });
    });
    growDocument(); // would re-assert 1200 if we were still armed
    expect(window.scrollY).toBe(300);
  });

  it("skips restore when nothing was saved", () => {
    renderHook(() => useScrollRestore(KEY, true));
    expect(window.scrollY).toBe(0);
  });
});

describe("useScrollRestore — regressions", () => {
  // The re-arm exists for StrictMode's double-mount, but `ready` also flips
  // true->false when the reader changes a filter. Re-arming there yanked the
  // newly filtered list back to the previous list's offset.
  it("does not re-restore when a filter change resets the list", () => {
    sessionStorage.setItem(KEY, "700");
    const { rerender } = renderHook(({ ready }) => useScrollRestore(KEY, ready), {
      initialProps: { ready: true },
    });
    expect(window.scrollY).toBe(700);

    act(() => {
      Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });
    });
    rerender({ ready: false }); // setStories(null) — new filter is loading
    rerender({ ready: true }); // filtered results arrive

    expect(window.scrollY).toBe(0); // 700 here means the stale-offset bug is back
  });

  // Blocked storage throws instead of returning null (in-app webviews — the
  // WhatsApp/Instagram browsers this app is shared into). An unguarded throw
  // inside the effect unwinds React and blanks the whole route, so assert on
  // the tree surviving rather than on the call not throwing: renderHook
  // swallows effect errors, which would make a .not.toThrow() assertion vacuous.
  it("survives storage being blocked, as in an in-app webview", async () => {
    const boom = () => {
      throw new DOMException("denied", "SecurityError");
    };
    // Stub the global, not Storage.prototype: jsdom's sessionStorage does not
    // route through the prototype, so a spyOn there is never called.
    vi.stubGlobal("sessionStorage", { getItem: boom, setItem: boom, clear: () => {} });
    // React logs a caught render error; keep the suite output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});

    function Feed() {
      useScrollRestore(KEY, true);
      return React.createElement("main", null, "story list");
    }
    render(React.createElement(Feed));
    expect(screen.getByText("story list")).toBeInTheDocument();

    scrollTo(400);
    await flushSave();
    // Still mounted => the throw never escaped the hook.
    expect(screen.getByText("story list")).toBeInTheDocument();
  });
});
