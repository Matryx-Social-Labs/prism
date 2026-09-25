"use client";

import { useEffect, useRef, useState } from "react";

/**
 * The record's section navigation (Design System v2 · Pages v3 · Story): on a
 * desk the "On this story" column with scroll-spy and mono counts, on the
 * phone a sticky row of tabs under the back bar. Both read the same list, in
 * the order the sections appear — a nav in another order is a small lie the
 * reader notices on the second tap. The read-progress hairline sits over both.
 */
export interface NavItem {
  id: string;
  label: string;
  count?: number;
}

/** Where a section's head lands under the sticky chrome when jumped to. */
const SPY_LINE = 160;

function reduced(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Scroll a section's head under the chrome; its scroll-margin does the offset. */
export function jumpTo(id: string): void {
  document.getElementById(id)?.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "start" });
}

/** The last section whose head has passed the spy line. */
function useScrollSpy(ids: string[]): string {
  const [active, setActive] = useState(ids[0] ?? "");
  const key = ids.join(" ");
  useEffect(() => {
    let raf = 0;
    const read = () => {
      let cur = ids[0] ?? "";
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < SPY_LINE) cur = id;
      }
      // At the foot of the page the last sections can never reach the line.
      const h = document.documentElement;
      if (ids.length && window.innerHeight + window.scrollY >= h.scrollHeight - 4 && h.scrollHeight > window.innerHeight) cur = ids[ids.length - 1];
      setActive(cur);
    };
    const onScroll = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(read); };
    window.addEventListener("scroll", onScroll, { passive: true });
    read();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("scroll", onScroll); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return active;
}

/** The 2px ink hairline across the top of the viewport: how far down the record you are. */
export function ReadProgress() {
  const bar = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let raf = 0;
    const read = () => {
      const h = document.documentElement;
      const p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
      if (bar.current) bar.current.style.transform = `scaleX(${Math.min(1, Math.max(0, p))})`;
    };
    const onScroll = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(read); };
    window.addEventListener("scroll", onScroll, { passive: true });
    read();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("scroll", onScroll); };
  }, []);
  return <div ref={bar} className="sc-progress" aria-hidden="true" style={{ width: "100%", transform: "scaleX(0)" }} />;
}

function onJump(e: React.MouseEvent, id: string) {
  e.preventDefault();
  jumpTo(id);
}

/** Desk: the "On this story" column. */
export function SectionRail({ items }: { items: NavItem[] }) {
  const active = useScrollSpy(items.map((n) => n.id));
  return (
    <aside className="hidden lg:block lg:sticky lg:top-[calc(var(--topbar)+28px)] lg:self-start" aria-label="On this story">
      <p className="p-eyebrow mb-2">On this story</p>
      <nav className="grid gap-0.5">
        {items.map((n) => {
          const on = active === n.id;
          return (
            <a
              key={n.id}
              href={`#${n.id}`}
              onClick={(e) => onJump(e, n.id)}
              aria-current={on ? "true" : undefined}
              className="flex min-h-[40px] items-center justify-between gap-3 border-l-2 px-2.5 text-[14px] leading-[1.2] transition-colors duration-150"
              style={{ borderColor: on ? "var(--ink)" : "var(--line)", color: on ? "var(--ink)" : "var(--ink-2)", fontWeight: on ? 600 : 500 }}
            >
              <span>{n.label}</span>
              {n.count != null && <span className="font-mono text-[11px] font-normal" style={{ color: "var(--ink-3)" }}>{n.count}</span>}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}

/** Phone: the same sections as a sticky row of tabs under the back bar. */
export function SectionTabs({ items }: { items: NavItem[] }) {
  const active = useScrollSpy(items.map((n) => n.id));
  const row = useRef<HTMLElement>(null);
  // Keep the tab in view as the reader scrolls past its section. The row's own
  // scroll, never scrollIntoView: that could move the page, and the page is
  // the reader's.
  useEffect(() => {
    const el = row.current?.querySelector<HTMLElement>(`[data-id="${active}"]`);
    if (!row.current || !el) return;
    const left = el.offsetLeft - (row.current.clientWidth - el.offsetWidth) / 2;
    row.current.scrollLeft = Math.max(0, left);
  }, [active]);
  return (
    <nav
      ref={row}
      aria-label="Sections"
      className="sc-tabs sticky top-[var(--masthead)] z-[25] px-2 lg:hidden"
      style={{ background: "var(--bg)" }}
    >
      {items.map((n) => (
        <a key={n.id} data-id={n.id} href={`#${n.id}`} onClick={(e) => onJump(e, n.id)} aria-current={active === n.id ? "true" : undefined} className="inline-flex min-h-[44px] items-center">
          {n.label}
        </a>
      ))}
    </nav>
  );
}
