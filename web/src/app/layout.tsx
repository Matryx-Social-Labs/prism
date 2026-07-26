import type { Metadata } from "next";
import Link from "next/link";
import { Fraunces, IBM_Plex_Mono } from "next/font/google";
import localFont from "next/font/local";
import { BottomTabBar } from "@/components/BottomTabBar";
import { SiteHeader } from "@/components/SiteHeader";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  axes: ["opsz", "SOFT", "WONK"],
});

// General Sans (ITF Free Font License, self-hosted — see src/fonts/general-sans/LICENSE.md).
// Replaces Space Grotesk per DESIGN.md: escape the AI-tool font convergence.
const ui = localFont({
  src: [
    { path: "../fonts/general-sans/GeneralSans-400.woff2", weight: "400" },
    { path: "../fonts/general-sans/GeneralSans-500.woff2", weight: "500" },
    { path: "../fonts/general-sans/GeneralSans-600.woff2", weight: "600" },
    { path: "../fonts/general-sans/GeneralSans-700.woff2", weight: "700" },
  ],
  variable: "--font-ui",
});

// Provenance voice (DESIGN.md): timestamps, sources, citations, funding labels.
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Parse — One story. Every perspective.",
    template: "%s — Parse",
  },
  description:
    "Role-aware AI news intelligence. The same story through your professional lens — with more lenses added continuously — all sides of the narrative, consequences, and a grounded agent you can ask.",
  openGraph: {
    type: "website",
    siteName: "Parse",
    title: "Parse — One story. Every perspective.",
    description: "Role-aware AI news intelligence. The same story, through your professional lens.",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Parse — One story. Every perspective.",
    description: "Role-aware AI news intelligence. The same story, through your professional lens.",
  },
};

// Runs before first paint: sets the saved theme, and marks the document as
// JS-capable. The `js` class gates the reveal animation — without it, .reveal
// set opacity:0 unconditionally and only a client effect ever restored it, so a
// crawler, a social-preview bot, or any reader whose JS failed got six blank
// content sections. Content is now visible by default and only hidden when we
// know something is there to un-hide it.
const themeInit = `(function(){document.documentElement.classList.add("js");try{var t=localStorage.getItem("prism.theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body
        className={`${display.variable} ${ui.variable} ${mono.variable} flex min-h-screen flex-col antialiased`}
        style={{ fontFamily: "var(--font-ui), system-ui, sans-serif" }}
      >
        <SiteHeader />
        <main className="w-full flex-1">{children}</main>
        <BottomTabBar />
        {/* Footer is desktop-only — on mobile the bottom tab bar is the chrome,
            and the marketing footer would just hide behind it. */}
        <footer className="mt-auto hidden border-t lg:block" style={{ borderColor: "var(--line)" }}>
          <div
            className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-2.5 px-5 py-6 text-xs sm:px-8 xl:px-10"
            style={{ color: "var(--ink-muted)" }}
          >
            <span>◮ Parse — role-aware news intelligence. Every claim traceable to its source.</span>
            <span className="flex items-center gap-3.5">
              <Link href="/about" className="underline underline-offset-[3px]">
                About &amp; labels
              </Link>
              <span style={{ color: "var(--ink-faint)" }}>Prototype · Matryx Social Labs</span>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
