import type { Metadata } from "next";
import Link from "next/link";
import { Fraunces, Space_Grotesk } from "next/font/google";
import { ThemeToggle } from "@/components/ThemeToggle";
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
        className={`${display.variable} ${ui.variable} min-h-screen antialiased`}
        style={{ fontFamily: "var(--font-ui), system-ui, sans-serif" }}
      >
        <div className="spectrum-bar h-[3px] w-full" aria-hidden />
        <header
          className="sticky top-0 z-40 border-b backdrop-blur-md"
          style={{ borderColor: "var(--line)", background: "var(--glass)" }}
        >
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
            <Link href="/" className="group flex items-center gap-2.5">
              <svg width="22" height="20" viewBox="0 0 24 22" aria-hidden className="shrink-0">
                <path
                  d="M12 1 L23 21 L1 21 Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinejoin="round"
                />
                <path d="M12 8 L12 21" stroke="url(#hg)" strokeWidth="1.6" />
                <defs>
                  <linearGradient id="hg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" />
                    <stop offset="50%" stopColor="#06b6d4" />
                    <stop offset="100%" stopColor="#8b5cf6" />
                  </linearGradient>
                </defs>
              </svg>
              <span
                className="text-xl font-semibold tracking-tight"
                style={{ fontFamily: "var(--font-display), serif" }}
              >
                Prism
              </span>
            </Link>
            <nav className="flex items-center gap-3 text-sm">
              <Link href="/feed" className="font-medium transition hover:opacity-70">
                Feed
              </Link>
              <Link
                href="/onboarding"
                className="rounded-full border px-3.5 py-1.5 text-xs font-semibold transition hover:opacity-70"
                style={{ borderColor: "var(--line-strong)" }}
              >
                Choose lens
              </Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        <footer className="mt-20 border-t" style={{ borderColor: "var(--line)" }}>
          <div
            className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-8 text-xs"
            style={{ color: "var(--ink-muted)" }}
          >
            <span>
              ◮ Prism — role-aware news intelligence. Every claim traceable to its source.
            </span>
            <span>Prototype · Matryx Social Labs</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
