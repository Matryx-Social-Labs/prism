"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { lensMeta } from "@/lib/lenses";
import { loadProfile } from "@/lib/profile";

export function HeaderNav() {
  const pathname = usePathname();
  const [lens, setLens] = useState<string | null>(null);

  useEffect(() => {
    setLens(loadProfile()?.lens ?? null);
  }, [pathname]);

  const m = lens ? lensMeta(lens) : null;

  return (
    <nav className="flex items-center gap-2">
      <Link
        href="/feed"
        className="px-2 py-1.5 text-[13.5px] font-medium"
        style={{ color: pathname === "/feed" ? "var(--ink)" : "var(--ink-muted)" }}
      >
        Feed
      </Link>
      <Link
        href="/about"
        className="hidden px-2 py-1.5 text-[13.5px] font-medium sm:block"
        style={{ color: pathname === "/about" ? "var(--ink)" : "var(--ink-muted)" }}
      >
        About
      </Link>
      {m && (
        <Link
          href="/interests"
          className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
          title="Your region, lens, and interests"
        >
          <span className="h-[7px] w-[7px] rounded-full" style={{ background: m.color }} />
          {m.short}
        </Link>
      )}
      <ThemeToggle />
    </nav>
  );
}
