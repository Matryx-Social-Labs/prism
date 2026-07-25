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
    // Nothing saved, so the restore never arms and `restoring` stays false —
    // otherwise the restore guard blocks the write and this passes without ever
    // exercising the `> 0` check it claims to cover.
    renderHook(() => useScrollRestore(KEY, true));
    scrollTo(640);
    await flushSave();
    expect(sessionStorage.getItem(KEY)).toBe("640");

    scrollTo(0); // tapping into a story yanks the still-mounted list to top
    await flushSave();
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

  // teardown() clears `restoring`. Without that, the flag stays true forever
  // after the first restore, the save guard drops every later scroll, and the
  // NEXT return-nav restores a stale offset — the exact failure this hook exists
  // to prevent.
  it("resumes saving once the reader takes over", async () => {
    sessionStorage.setItem(KEY, "1200");
    renderHook(() => useScrollRestore(KEY, true));
    expect(window.scrollY).toBe(1200);

    act(() => {
      window.dispatchEvent(new Event("touchstart"));
    });
    scrollTo(300);
    await flushSave();
    expect(sessionStorage.getItem(KEY)).toBe("300");
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

  // Next keeps the component mounted when only a dynamic segment changes, so
  // /sector/a -> /sector/b reuses these refs. Latching on the instance instead
  // of the key meant sector B never restored its own offset.
  it("re-arms when the key changes, as on /sector/a -> /sector/b", () => {
    sessionStorage.setItem("sector:a:scrollY", "400");
    sessionStorage.setItem("sector:b:scrollY", "900");
    const { rerender } = renderHook(({ k }) => useScrollRestore(k, true), {
      initialProps: { k: "sector:a:scrollY" },
    });
    expect(window.scrollY).toBe(400);

    // Settle sector A first — the reader touching the page is what makes this
    // bite. While unsettled the teardown's re-arm masks it, so a test that
    // switches keys immediately passes with or without the key latch.
    act(() => {
      window.dispatchEvent(new Event("touchstart"));
    });

    rerender({ k: "sector:b:scrollY" });
    expect(window.scrollY).toBe(900); // 400 => the key latch is back
  });

  it("does not restore a key that has nothing saved", () => {
    sessionStorage.setItem("sector:a:scrollY", "400");
    const { rerender } = renderHook(({ k }) => useScrollRestore(k, true), {
      initialProps: { k: "sector:a:scrollY" },
    });
    expect(window.scrollY).toBe(400);
    rerender({ k: "sector:fresh:scrollY" });
    expect(window.scrollY).toBe(400); // no saved offset => leave the page alone
  });

  // The other half of the same branch: StrictMode's dev double-mount tears the
  // restore down before it settles, and the re-arm is what lets the remount
  // finish it. Without this, scroll restore could be dead in dev unnoticed.
  it("still restores through StrictMode's double-mount", () => {
    sessionStorage.setItem(KEY, "700");
    function Feed() {
      useScrollRestore(KEY, true);
      return React.createElement("main", null, "story list");
    }
    render(React.createElement(Feed), { reactStrictMode: true });
    expect(window.scrollY).toBe(700);

    // Asserting the position alone proves nothing: the FIRST mount already set
    // it. What the re-arm actually buys is a live observer on the second mount,
    // so late-loading images still get corrected. Drift the position and grow
    // the document — only a connected observer pulls it back.
    act(() => {
      Object.defineProperty(window, "scrollY", { value: 250, writable: true, configurable: true });
    });
    growDocument();
    expect(window.scrollY).toBe(700);
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
