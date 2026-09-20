"use client";

import { useEffect, useRef, useState } from "react";

// A sticky rail that behaves like a reader expects (DESIGN.md § Layout): when
// it fits the viewport it holds at the top; when it is TALLER than the
// viewport — a record with thirty reports — it scrolls with the page until
// its own end is in view and holds there, so nothing in it is out of reach
// until the main column runs out. Measured, not guessed: a ResizeObserver
// re-decides when the rail or the window changes.
export function Rail({ children, className = "", label }: { children: React.ReactNode; className?: string; label?: string }) {
  const ref = useRef<HTMLElement>(null);
  const [tall, setTall] = useState(false);
  const [desk, setDesk] = useState(false); // a rail only exists beside the column, from lg
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const mq = window.matchMedia("(min-width: 1024px)");
    const decide = () => {
      setDesk(mq.matches);
      setTall(el.offsetHeight > window.innerHeight - 100);
    };
    decide();
    const ro = new ResizeObserver(decide);
    ro.observe(el);
    window.addEventListener("resize", decide);
    mq.addEventListener("change", decide);
    return () => { ro.disconnect(); window.removeEventListener("resize", decide); mq.removeEventListener("change", decide); };
  }, []);
  return (
    <aside
      ref={ref}
      aria-label={label}
      className={`${className} ${tall ? "self-end" : "self-start"}`}
      style={desk ? { position: "sticky", ...(tall ? { bottom: 24 } : { top: "calc(var(--topbar) + 24px)" }) } : undefined}
    >
      {children}
    </aside>
  );
}
