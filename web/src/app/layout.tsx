import type { Metadata } from "next";
import Link from "next/link";
import { Fraunces, Space_Grotesk } from "next/font/google";
import { HeaderNav } from "@/components/HeaderNav";
import { PrismMark } from "@/components/PrismMark";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  axes: ["opsz", "SOFT", "WONK"],
});

const ui = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-ui",
});

export const metadata: Metadata = {
  title: "Prism — One event. Every angle.",
  description:
    "Role-aware AI news intelligence. The same story through your professional lens — cyber, markets, or simply staying informed — with both sides, consequences, and a grounded agent you can ask.",
};

const themeInit = `(function(){try{var t=localStorage.getItem("prism.theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body
        className={`${display.variable} ${ui.variable} flex min-h-screen flex-col antialiased`}
        style={{ fontFamily: "var(--font-ui), system-ui, sans-serif" }}
      >
        <div className="spectrum-bar h-[3px] w-full" aria-hidden />
        <header
          className="sticky top-0 z-40 border-b backdrop-blur-md"
          style={{ borderColor: "var(--line)", background: "var(--glass)" }}
        >
          <div className="mx-auto flex max-w-[1080px] items-center justify-between gap-3 px-5 py-[11px]">
            <Link href="/" className="flex items-center gap-2.5" style={{ color: "var(--ink)" }}>
              <PrismMark />
              <span
                className="text-xl font-semibold tracking-tight"
                style={{ fontFamily: "var(--font-display), serif" }}
              >
                Prism
              </span>
            </Link>
            <HeaderNav />
          </div>
        </header>
        <main className="w-full flex-1">{children}</main>
        <footer className="mt-auto border-t" style={{ borderColor: "var(--line)" }}>
          <div
            className="mx-auto flex max-w-[1080px] flex-wrap items-center justify-between gap-2.5 px-5 py-6 text-xs"
            style={{ color: "var(--ink-muted)" }}
          >
            <span>◮ Prism — role-aware news intelligence. Every claim traceable to its source.</span>
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
