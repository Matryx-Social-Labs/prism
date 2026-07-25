"use client";

import { useEffect, useRef } from "react";

// Restore window scroll on return-navigation to a list page. Save while the reader
// scrolls (guarded against the spurious 0 the router writes when they tap into a
// detail page), then restore once `ready` — the list's data is present — and
// re-assert for a short window to beat the router's post-nav scroll reset and any
// late content growth. Extracted from the feed; reused by trending/search/sector.
export function useScrollRestore(key: string, ready: boolean) {
  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (window.scrollY > 0) sessionStorage.setItem(key, String(window.scrollY));
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, [key]);

  const restored = useRef(false);
  useEffect(() => {
    if (restored.current || !ready) return;
    restored.current = true;
    const y = Number(sessionStorage.getItem(key) || 0);
    if (y <= 0) return;
    const start = performance.now();
    const tick = () => {
      window.scrollTo(0, y);
      if (performance.now() - start < 300 && Math.abs(window.scrollY - y) > 2) {
        requestAnimationFrame(tick);
      }
    };
    requestAnimationFrame(tick);
  }, [key, ready]);
}
