import type { Metadata, Viewport } from "next";
import { NavMemory } from "@/components/NavMemory";
import { UsageBeacon } from "@/components/UsageBeacon";
import { Anek_Bangla, Anek_Devanagari, Anek_Gujarati, Anek_Gurmukhi, Anek_Kannada, Anek_Latin, Anek_Malayalam, Anek_Odia, Anek_Tamil, Anek_Telugu, Geist_Mono, Newsreader, Noto_Naskh_Arabic, Noto_Nastaliq_Urdu, Noto_Serif_Bengali, Noto_Serif_Devanagari, Noto_Serif_Gujarati, Noto_Serif_Gurmukhi, Noto_Serif_Kannada, Noto_Serif_Malayalam, Noto_Serif_Oriya, Noto_Serif_Tamil, Noto_Serif_Telugu } from "next/font/google";
import { BottomTabBar } from "@/components/BottomTabBar";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { jsonLd, siteGraph } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

// THREE VOICES (Design System v2, tokens/typography.css). A word in the wrong
// voice is a bug. Every family sets a variable named --font-<family> on <html>;
// the voice stacks (--font-record, --font-read, --font-mono) are generated onto
// :root from design/tokens.json, the same element, so they resolve.
//
// The record — headlines, titles, quotes, hero figures: Newsreader (drawn for
// news, optical sizes), then a Noto Serif per Indic script and Nastaliq for Urdu.
const newsreader = Newsreader({ subsets: ["latin"], weight: "variable", style: ["normal", "italic"], axes: ["opsz"], variable: "--font-newsreader" });
// The Indic faces are unicode-ranged to their script and not preloaded: the
// browser fetches one only when a glyph needs it. next/font has no metrics for
// them, so it cannot size a fallback (adjustFontFallback off, as before).
// next/font reads these calls statically, so the options are spelled out.
const recordHi = Noto_Serif_Devanagari({ subsets: ["devanagari"], weight: "variable", variable: "--font-noto-serif-devanagari", preload: false, adjustFontFallback: false });
const recordKn = Noto_Serif_Kannada({ subsets: ["kannada"], weight: "variable", variable: "--font-noto-serif-kannada", preload: false, adjustFontFallback: false });
const recordTa = Noto_Serif_Tamil({ subsets: ["tamil"], weight: "variable", variable: "--font-noto-serif-tamil", preload: false, adjustFontFallback: false });
const recordTe = Noto_Serif_Telugu({ subsets: ["telugu"], weight: "variable", variable: "--font-noto-serif-telugu", preload: false, adjustFontFallback: false });
const recordBn = Noto_Serif_Bengali({ subsets: ["bengali"], weight: "variable", variable: "--font-noto-serif-bengali", preload: false, adjustFontFallback: false });
const recordGu = Noto_Serif_Gujarati({ subsets: ["gujarati"], weight: "variable", variable: "--font-noto-serif-gujarati", preload: false, adjustFontFallback: false });
const recordPa = Noto_Serif_Gurmukhi({ subsets: ["gurmukhi"], weight: "variable", variable: "--font-noto-serif-gurmukhi", preload: false, adjustFontFallback: false });
const recordMl = Noto_Serif_Malayalam({ subsets: ["malayalam"], weight: "variable", variable: "--font-noto-serif-malayalam", preload: false, adjustFontFallback: false });
const recordOr = Noto_Serif_Oriya({ subsets: ["oriya"], weight: "variable", variable: "--font-noto-serif-oriya", preload: false, adjustFontFallback: false });
const recordUr = Noto_Nastaliq_Urdu({ subsets: ["arabic"], weight: "variable", variable: "--font-noto-nastaliq-urdu", preload: false, adjustFontFallback: false });

// Reading and UI — everything read or tapped: Anek (Ek Type), one Indic-first
// design across Latin, Devanagari, Kannada, Tamil, Telugu, Bangla, Gujarati,
// Gurmukhi, Malayalam and Odia;
// Noto Naskh Arabic for Urdu.
const readLatin = Anek_Latin({ subsets: ["latin"], weight: "variable", variable: "--font-anek-latin" });
const readHi = Anek_Devanagari({ subsets: ["devanagari"], weight: "variable", variable: "--font-anek-devanagari", preload: false, adjustFontFallback: false });
const readKn = Anek_Kannada({ subsets: ["kannada"], weight: "variable", variable: "--font-anek-kannada", preload: false, adjustFontFallback: false });
const readTa = Anek_Tamil({ subsets: ["tamil"], weight: "variable", variable: "--font-anek-tamil", preload: false, adjustFontFallback: false });
const readTe = Anek_Telugu({ subsets: ["telugu"], weight: "variable", variable: "--font-anek-telugu", preload: false, adjustFontFallback: false });
const readBn = Anek_Bangla({ subsets: ["bengali"], weight: "variable", variable: "--font-anek-bangla", preload: false, adjustFontFallback: false });
const readGu = Anek_Gujarati({ subsets: ["gujarati"], weight: "variable", variable: "--font-anek-gujarati", preload: false, adjustFontFallback: false });
const readPa = Anek_Gurmukhi({ subsets: ["gurmukhi"], weight: "variable", variable: "--font-anek-gurmukhi", preload: false, adjustFontFallback: false });
const readMl = Anek_Malayalam({ subsets: ["malayalam"], weight: "variable", variable: "--font-anek-malayalam", preload: false, adjustFontFallback: false });
const readOr = Anek_Odia({ subsets: ["oriya"], weight: "variable", variable: "--font-anek-odia", preload: false, adjustFontFallback: false });
const readUr = Noto_Naskh_Arabic({ subsets: ["arabic"], weight: "variable", variable: "--font-noto-naskh-arabic", preload: false, adjustFontFallback: false });

// Provenance ONLY: times, counts, [n], outlet codes, tickers, CVE ids. Tabular.
const mono = Geist_Mono({ subsets: ["latin"], weight: "variable", variable: "--font-geist-mono" });

const FONT_VARIABLES = [newsreader, recordHi, recordKn, recordTa, recordTe, recordBn, recordGu, recordPa, recordMl, recordOr, recordUr, readLatin, readHi, readKn, readTa, readTe, readBn, readGu, readPa, readMl, readOr, readUr, mono]
  .map((f) => f.variable)
  .join(" ");

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: "Prism",
  title: {
    default: "Prism: Follow the story, not the headlines.",
    template: "%s | Prism",
  },
  description:
    "One live story record from monitored outlets, with every development, verified quote and source open to inspection.",
  // Let search show the full snippet and the share card at full size; a news
  // result cut to 160 characters or a thumbnail loses the record's point.
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-snippet": -1, "max-image-preview": "large", "max-video-preview": -1 } },
  category: "news",
  publisher: "Prism Media Intelligence LLP",
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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F6F2" },
    { media: "(prefers-color-scheme: dark)", color: "#0F1114" },
  ],
};

// Runs before first paint: sets the saved theme, and marks the document as
// JS-capable (the `js` class gates anything that must never hide content from
// a crawler or a reader whose JS failed).
const themeInit = `(function(){document.documentElement.classList.add("js");try{var t=localStorage.getItem("prism.theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={FONT_VARIABLES} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
        {/* Who publishes this and how to search it — the same on every page (lib/seo). */}
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(siteGraph()) }} />
      </head>
      <body className="flex min-h-dvh flex-col antialiased">
        <a
          href="#main-content"
          className="btn btn-primary btn-sm fixed left-3 top-3 z-[100] -translate-y-20 focus:translate-y-0"
        >
          Skip to the record
        </a>
        {/* Aggregate counts only, cookieless (lib/analytics.ts); absent until the domain is configured. */}
        <UsageBeacon />
        <NavMemory />
        <SiteHeader />
        <main id="main-content" tabIndex={-1} className="w-full flex-1 outline-none">{children}</main>
        <BottomTabBar />
        <SiteFooter />
      </body>
    </html>
  );
}
