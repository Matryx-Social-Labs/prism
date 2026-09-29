"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId } from "react";
import { Brand } from "@/components/Brand";
import { OWN_CHROME, hasPhoneBar } from "@/components/SiteHeader";
import { ThemeSeg } from "@/components/accounts/ThemeChoice";
import { CONTACT_EMAIL } from "@/lib/legal";

// Two groups, so fifteen links stay scannable: the record and how it is made,
// then the policies and the ways to reach Prism (Grievance and Delivery are
// required pages: docs/COMPLIANCE-INDIA.md N1, N9).
const GROUPS: { title: string; links: [string, string][] }[] = [
  {
    title: "The record",
    links: [
      ["/about", "How it works"],
      ["/about#status", "What\u2019s live"],
      ["/sources", "Sources"],
      ["/corrections", "Corrections"],
      ["/state", "States"],
      ["/archive", "Archive"],
      ["/plus?from=footer", "Plus"], // the door, counted on /plus (common/usage.SUBSCRIBE_DETAIL)
    ],
  },
  {
    title: "Policies and contact",
    links: [
      ["/privacy", "Privacy"],
      ["/terms", "Terms"],
      ["/refunds", "Refunds"],
      ["/delivery", "Delivery"],
      ["/grievance", "Grievance"],
      ["/press", "Press"],
      ["/for-publishers", "For publishers"],
      [`mailto:${CONTACT_EMAIL}`, "Contact"],
    ],
  },
];
const LINK = "inline-flex min-h-11 items-center hover:underline lg:min-h-8";

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
      <div className="mx-auto flex max-w-[var(--shell)] flex-wrap items-start gap-x-6 gap-y-4 px-[var(--gutter)] py-5 text-[13.5px] leading-[1.4]" style={{ color: "var(--ink-2)" }}>
        <span className="flex flex-[1_1_320px] flex-wrap items-center gap-3"><Brand size={18} /><span>Prism Media Intelligence LLP · built with Matrix Social Labs</span></span>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-10 gap-y-3">
          {GROUPS.map((g) => (
            <div key={g.title} className="grid content-start gap-1">
              <p className="p-eyebrow">{g.title}</p>
              <ul className="flex max-w-[420px] flex-wrap gap-x-5">
                {g.links.map(([href, label]) => (
                  <li key={href}>
                    {href.startsWith("mailto:")
                      ? <a href={href} className={LINK} style={{ color: "var(--ink-2)" }}>{label}</a>
                      : <Link href={href} className={LINK} style={{ color: "var(--ink-2)" }}>{label}</Link>}
                  </li>
                ))}
              </ul>
            </div>
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
