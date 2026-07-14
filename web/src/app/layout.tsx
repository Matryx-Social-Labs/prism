import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prism — Security News Intelligence",
  description:
    "Role-aware news intelligence: both sides of every story, what it means for you, and an agent you can ask.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-stone-200 dark:border-stone-800">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
            <Link href="/" className="text-xl font-bold tracking-tight">
              ◮ Prism
            </Link>
            <span className="text-xs uppercase tracking-widest text-stone-500">
              Cyber / GRC edition — prototype
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-4xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
