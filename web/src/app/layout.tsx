import type { Metadata } from "next";
import Link from "next/link";
import { Hind, Hind_Guntur, Hind_Madurai, Hind_Mysuru, Martian_Mono, Teko } from "next/font/google";
import { BottomTabBar } from "@/components/BottomTabBar";
import { SiteHeader } from "@/components/SiteHeader";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

// THREE VOICES, FROM THE SUBJECT'S WORLD (the reservation chart; see
// .impeccable/surfaces and PRODUCT.md § Brand Commitments). The rule is the
// commitment — a structural voice, a reading voice, a provenance voice — and the
// faces are chosen for this world, not inherited from the last one.
//
// Structure: Teko (Indian Type Foundry). The condensed signage of station boards
// and train names on the chart. Masthead labels, the sector strip, section
// heads, the ticket's big numbers. Never running text.
const display = Teko({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-display",
});

// Reading: Hind (ITF) and its script siblings. One family across Latin,
// Devanagari, Kannada, Tamil and Telugu, so a Kannada headline and an English
// one sit on the same page without a fallback seam — the browser falls through
// the stack per glyph. Headlines, body, quotes: everything a reader reads.
const ui = Hind({ subsets: ["latin", "devanagari"], weight: ["400", "500", "600", "700"], variable: "--font-hind" });
// next/font has no metrics table for the Indic siblings, so it cannot size a
// fallback face to them and logs "Failed to find font override values" on
// every build. Off explicitly: these families only ever set a line or two of
// a non-Latin headline, so the shift a sized fallback prevents is negligible.
const uiKannada = Hind_Mysuru({ subsets: ["kannada"], weight: ["400", "500", "600"], variable: "--font-hind-kn", adjustFontFallback: false });
const uiTamil = Hind_Madurai({ subsets: ["tamil"], weight: ["400", "500", "600"], variable: "--font-hind-ta", adjustFontFallback: false });
const uiTelugu = Hind_Guntur({ subsets: ["telugu"], weight: ["400", "500", "600"], variable: "--font-hind-te", adjustFontFallback: false });

// Provenance ONLY: source counts, times, origins, codes, [n], tickers, CVE ids.
// Tabular by design. Never prose, never a heading.
const mono = Martian_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Prism: One story. Every perspective.",
    template: "%s | Prism",
  },
  description:
    "Every outlet's report of one event, gathered into one story you can re-read through a professional lens. Who said what, verbatim, and which outlets.",
  openGraph: {
    type: "website",
    siteName: "Prism",
    title: "Prism: One story. Every perspective.",
    description: "Every outlet's report of one event, gathered into one story you can re-read through a professional lens.",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Prism: One story. Every perspective.",
    description: "Every outlet's report of one event, gathered into one story you can re-read through a professional lens.",
  },
};

// Runs before first paint: sets the saved theme, and marks the document as
// JS-capable (the `js` class gates anything that must never hide content from
// a crawler or a reader whose JS failed).
const themeInit = `(function(){document.documentElement.classList.add("js");try{var t=localStorage.getItem("prism.theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body
        className={`${display.variable} ${ui.variable} ${uiKannada.variable} ${uiTamil.variable} ${uiTelugu.variable} ${mono.variable} flex min-h-screen flex-col antialiased`}
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
            <span>Prism. Every claim traceable to its source.</span>
            <span className="flex items-center gap-3.5">
              <Link href="/about" className="underline underline-offset-[3px]">
                About
              </Link>
              <span style={{ color: "var(--ink-faint)" }}>Prototype · Matryx Social Labs</span>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
