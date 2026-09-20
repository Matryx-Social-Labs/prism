import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import { PLAUSIBLE_DOMAIN } from "@/lib/analytics";
import { Hind, Hind_Guntur, Hind_Madurai, Hind_Mysuru, JetBrains_Mono, Newsreader, Noto_Serif_Kannada, Noto_Serif_Tamil, Noto_Serif_Telugu, Tiro_Devanagari_Hindi } from "next/font/google";
import { BottomTabBar } from "@/components/BottomTabBar";
import { SiteHeader } from "@/components/SiteHeader";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

// THREE VOICES (DESIGN.md § Typography — the Spectrum world, 2026-09-18). The
// rule is the commitment — a record voice, a reading voice, a provenance voice.
//
// The record: Newsreader (Production Type), drawn for on-screen news reading with
// real optical sizes, so a 60px promise and a 19px row headline come from one
// voice. Headlines, story titles, section titles, quotes. Never a button or label.
const display = Newsreader({
  subsets: ["latin"],
  weight: "variable", // the whole wght axis; opsz rides along so 60px and 19px set from one face
  style: ["normal", "italic"],
  axes: ["opsz"],
  variable: "--font-display",
});
// The record voice per script: Newsreader has no Indic glyphs, so without these
// a Hindi outlet headline in "What changed" or a Kannada quote fell to the
// system sans inside a serif row. Not preloaded: each face is unicode-ranged to
// its script and the browser fetches it only when a glyph needs it.
// (next/font reads these calls statically, so the options are spelled out.)
const recordHi = Tiro_Devanagari_Hindi({ subsets: ["devanagari"], weight: "400", style: ["normal", "italic"], variable: "--font-record-hi", preload: false, adjustFontFallback: false });
const recordKn = Noto_Serif_Kannada({ subsets: ["kannada"], weight: "variable", variable: "--font-record-kn", preload: false, adjustFontFallback: false });
const recordTa = Noto_Serif_Tamil({ subsets: ["tamil"], weight: "variable", style: ["normal", "italic"], variable: "--font-record-ta", preload: false, adjustFontFallback: false });
const recordTe = Noto_Serif_Telugu({ subsets: ["telugu"], weight: "variable", variable: "--font-record-te", preload: false, adjustFontFallback: false });

// Reading and UI: Hind (ITF) and its script siblings. One family across Latin,
// Devanagari, Kannada, Tamil and Telugu, so a Kannada row and an English one sit
// on the same baseline without a fallback seam — the browser falls through per glyph.
const ui = Hind({ subsets: ["latin", "devanagari"], weight: ["400", "500", "600", "700"], variable: "--font-hind" });
// next/font has no metrics table for the Indic siblings, so it cannot size a
// fallback face to them and logs "Failed to find font override values" on
// every build. Off explicitly: these families only ever set a line or two of
// a non-Latin headline, so the shift a sized fallback prevents is negligible.
const uiKannada = Hind_Mysuru({ subsets: ["kannada"], weight: ["400", "500", "600"], variable: "--font-hind-kn", adjustFontFallback: false });
const uiTamil = Hind_Madurai({ subsets: ["tamil"], weight: ["400", "500", "600"], variable: "--font-hind-ta", adjustFontFallback: false });
const uiTelugu = Hind_Guntur({ subsets: ["telugu"], weight: ["400", "500", "600"], variable: "--font-hind-te", adjustFontFallback: false });

// Provenance ONLY: times, counts, codes, [n], tickers, CVE ids. Tabular by
// design, narrow enough for a time and a count beside a 26px monogram.
const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Prism: Follow the story, not the headlines.",
    template: "%s | Prism",
  },
  description:
    "One live story record from monitored outlets, with every development, verified quote and source open to inspection.",
  openGraph: {
    type: "website",
    siteName: "Prism",
    title: "Prism: Follow the story, not the headlines.",
    description: "One live story record from monitored outlets, with every development, verified quote and source open to inspection.",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Prism: Follow the story, not the headlines.",
    description: "One live story record from monitored outlets, with every development, verified quote and source open to inspection.",
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
        className={`${display.variable} ${recordHi.variable} ${recordKn.variable} ${recordTa.variable} ${recordTe.variable} ${ui.variable} ${uiKannada.variable} ${uiTamil.variable} ${uiTelugu.variable} ${mono.variable} flex min-h-dvh flex-col antialiased`}
        style={{ fontFamily: "var(--font-ui), system-ui, sans-serif" }}
      >
        <a
          href="#main-content"
          className="btn btn-secondary fixed left-3 top-3 z-[100] -translate-y-20 focus:translate-y-0"
        >
          Skip to content
        </a>
        {/* Aggregate counts only, cookieless (lib/analytics.ts); absent until the domain is configured. */}
        {PLAUSIBLE_DOMAIN && <Script defer data-domain={PLAUSIBLE_DOMAIN} src="https://plausible.io/js/script.js" strategy="afterInteractive" />}
        <SiteHeader />
        <main id="main-content" tabIndex={-1} className="w-full flex-1 outline-none">{children}</main>
        <BottomTabBar />
        {/* Footer is desktop-only — on mobile the bottom tab bar is the chrome,
            and the marketing footer would just hide behind it. */}
        <footer className="mt-auto hidden border-t lg:block" style={{ borderColor: "var(--line)" }}>
          <div
            className="mx-auto flex max-w-[var(--shell)] flex-wrap items-center justify-between gap-2.5 px-5 py-6 text-[13px] sm:px-8 xl:px-10"
            style={{ color: "var(--ink-3)" }}
          >
            <span>Prism · Prism Media Intelligence LLP · built with Matrix Social Labs</span>
            <span className="flex items-center gap-4">
              <Link href="/about" className="hover:underline underline-offset-[3px]">About</Link>
              <Link href="/about#status" className="hover:underline underline-offset-[3px]">What&rsquo;s live</Link>
              <Link href="/plus" className="hover:underline underline-offset-[3px]">Plus</Link>
              <Link href="/privacy" className="hover:underline underline-offset-[3px]">Privacy</Link>
              <Link href="/terms" className="hover:underline underline-offset-[3px]">Terms</Link>
              <Link href="/refunds" className="hover:underline underline-offset-[3px]">Refunds</Link>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
