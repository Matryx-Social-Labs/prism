"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId } from "react";
import { Brand } from "@/components/Brand";
import { OWN_CHROME, hasPhoneBar } from "@/components/SiteHeader";
import { ThemeSeg } from "@/components/accounts/ThemeChoice";

const LINKS: [string, string][] = [
  ["/about", "How it works"],
  ["/about#status", "What\u2019s live"],
  ["/sources", "Sources"],
  ["/corrections", "Corrections"],
  ["/plus", "Plus"],
  ["/privacy", "Privacy"],
  ["/terms", "Terms"],
  ["/refunds", "Refunds"],
];

/**
 * The footer (Design System v2 · Footer). On a phone it shows only on the pages with
 * the phone bar (the landing, /about, /plus), where its Appearance row is the theme
 * control (screens/PhoneBar.html); in the app the tab bar is the chrome and a footer
 * would hide behind it. Absent where a tool has its own chrome.
 */
export function SiteFooter() {
  const pathname = usePathname();
  const appearance = useId();
  if (OWN_CHROME.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;
  return (
    <footer className={`mt-auto border-t ${hasPhoneBar(pathname) ? "" : "hidden lg:block"}`} style={{ borderColor: "var(--line)", background: "var(--sunken)" }}>
      <div className="mx-auto flex max-w-[var(--shell)] flex-wrap items-center gap-x-6 gap-y-2.5 px-[var(--gutter)] py-5 text-[13.5px] leading-[1.4]" style={{ color: "var(--ink-2)" }}>
        <span className="flex flex-[1_1_320px] flex-wrap items-center gap-3"><Brand size={18} /><span>Prism Media Intelligence LLP · built with Matrix Social Labs</span></span>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
          {LINKS.map(([href, label]) => (
            <Link key={href} href={href} className="inline-flex min-h-11 items-center hover:underline lg:min-h-8" style={{ color: "var(--ink-2)" }}>{label}</Link>
          ))}
        </nav>
        <div className="flex basis-full flex-wrap items-center gap-x-3.5 gap-y-2 border-t pt-3.5" style={{ borderColor: "var(--line)" }}>
          <span id={appearance} className="p-eyebrow">Appearance</span>
          <ThemeSeg labelledBy={appearance} />
        </div>
      </div>
    </footer>
  );
}
