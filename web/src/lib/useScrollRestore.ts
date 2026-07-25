"use client";

import { useEffect, useRef } from "react";

// Restore window scroll on return-navigation to a list page. Save while the reader
// scrolls (guarded against the spurious 0 the router writes when they tap into a
// detail page), then restore once `ready` — the list's data is present.
//
// Restoring is not a single scrollTo: images and lazy content land after the first
// paint and grow the document, so an early scrollTo clamps short and the reader
// ends up near, but not at, where they left. So we re-assert on every document
// resize until the position sticks — and bail out the instant the reader acts, so
// we never fight their input.
const SETTLE_MS = 3000; // hard stop: nothing should still be growing after this
const STOP_EVENTS = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
// Storage throws instead of returning null when it's blocked — in-app webviews
// (the WhatsApp/Instagram browsers this app is shared into) do exactly that.
// A throw inside an effect unwinds React and blanks the route, so never let one out.
function readY(key: string): number {
  try {
    const y = Number(sessionStorage.getItem(key) || 0);
    // A corrupt value yields NaN, which slips past a `y <= 0` guard and then
    // holds the restore open — suppressing every save — for the full settle.
    return Number.isFinite(y) ? y : 0;
  } catch {
    return 0;
  }
}
function clearY(key: string) {
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* storage blocked */
  }
}
function writeY(key: string, y: number) {
  try {
    sessionStorage.setItem(key, String(y));
  } catch {
    /* storage blocked — scroll restore is a nicety, not worth a crash */
  }
}

export function useScrollRestore(key: string, ready: boolean) {
  // While restoring, scrollTo may clamp to a still-short page; that intermediate
  // position must not overwrite the saved target.
  const restoring = useRef(false);
  // Latest `ready`, readable from the effect cleanup (which closes over the OLD
  // value). Refs update during render, before cleanup runs — so this tells the
  // cleanup WHY it fired. See the re-arm note below.
  const readyRef = useRef(ready);
  readyRef.current = ready;

  useEffect(() => {
    let raf = 0;
    let zeroTimer: ReturnType<typeof setTimeout> | undefined;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      clearTimeout(zeroTimer);
      raf = requestAnimationFrame(() => {
        if (restoring.current) return;
        if (window.scrollY > 0) {
          writeY(key, window.scrollY);
          return;
        }
        // Two different zeros reach here: the reader deliberately scrolling back
        // to top, and the router yanking the still-mounted list to top as they
        // tap into a story. Persisting the second would clobber their place;
        // ignoring the first strands them at a stale offset on return. Tell them
        // apart by dwell — the router's zero is followed immediately by unmount,
        // which clears this timer, while a real scroll-to-top stays at 0.
        zeroTimer = setTimeout(() => clearY(key), 200);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
      clearTimeout(zeroTimer);
    };
  }, [key]);

  const restored = useRef(false);
  // Next does not remount a client component when only a dynamic segment
  // changes, so /sector/a -> /sector/b keeps these refs. Without re-arming on
  // the key, sector B never restores its own offset (and, inside the settle
  // window, could restore it onto A's still-rendered list).
  const lastKey = useRef(key);
  if (lastKey.current !== key) {
    lastKey.current = key;
    restored.current = false;
  }

  useEffect(() => {
    if (restored.current || !ready) return;
    restored.current = true;
    const y = readY(key);
    if (y <= 0) return;

    restoring.current = true;
    let settled = false;
    const assert = () => {
      if (Math.abs(window.scrollY - y) > 1) window.scrollTo(0, y);
    };
    const teardown = () => {
      restoring.current = false;
      observer.disconnect();
      clearTimeout(timer);
      for (const ev of STOP_EVENTS) window.removeEventListener(ev, stop);
    };
    // The reader scrolled or tapped — they own the viewport now.
    const stop = () => {
      settled = true;
      teardown();
    };
    // <html> height is viewport-locked in some layouts; <body> tracks content.
    const observer = new ResizeObserver(assert);
    const timer = setTimeout(stop, SETTLE_MS);
    for (const ev of STOP_EVENTS) window.addEventListener(ev, stop, { passive: true });
    observer.observe(document.documentElement);
    observer.observe(document.body);
    assert();

    return () => {
      teardown();
      // Torn down before the restore settled — StrictMode's double-mount does
      // exactly this, so re-arm and let the remount finish the restore.
      // But `ready` ALSO flips true->false when the reader changes a filter
      // (trending/sector re-fetch), and re-arming there would yank the new,
      // differently-sized list back to the old list's offset. readyRef tells
      // the two apart: still true => remount/unmount, false => the list changed.
      if (!settled && readyRef.current) restored.current = false;
    };
  }, [key, ready]);
}
