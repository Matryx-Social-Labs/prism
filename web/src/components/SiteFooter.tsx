"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { OWN_CHROME } from "@/components/SiteHeader";

const LINKS: [string, string][] = [
  ["/about", "About"],
  ["/about#status", "What\u2019s live"],
  ["/sources", "Sources"],
  ["/corrections", "Corrections"],
  ["/plus", "Plus"],
  ["/privacy", "Privacy"],
  ["/terms", "Terms"],
  ["/refunds", "Refunds"],
];

/**
 * The footer (Design System v2 · Footer): desk only — on the phone the tab bar is
 * the chrome and a footer would hide behind it. Absent where a tool has its own chrome.
 */
export function SiteFooter() {
  const pathname = usePathname();
  if (OWN_CHROME.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;
  return (
    <footer className="mt-auto hidden border-t lg:block" style={{ borderColor: "var(--line)", background: "var(--sunken)" }}>
      <div className="mx-auto flex max-w-[var(--shell)] flex-wrap items-center gap-x-6 gap-y-2.5 px-[var(--gutter)] py-5 text-[13.5px] leading-[1.4]" style={{ color: "var(--ink-2)" }}>
        <span className="flex-[1_1_320px]">Prism · Prism Media Intelligence LLP · built with Matrix Social Labs</span>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
          {LINKS.map(([href, label]) => (
            <Link key={href} href={href} className="inline-flex min-h-8 items-center hover:underline" style={{ color: "var(--ink-2)" }}>{label}</Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
