import Link from "next/link";
import { PrismMark } from "@/components/PrismMark";

/**
 * The wordmark lockup: the mark (the logo — unchanged) and readPrism.news as one
 * word in the record voice — "read" and ".news" regular in ink-3, "Prism"
 * semibold in ink (Design System v2 · screens/Wordmark.html, adopted 2026-09-28).
 * The lockup is the address because prism.news is someone else's: a reader who
 * remembers only "Prism" types the bare name and lands on a parked page. The
 * link's name is its visible text, so a screen reader says the address too.
 * The name in running text stays Prism. The share cards (lib/ogCard Frame) and
 * the email masthead (common/email_templates shell) set the same split by hand:
 * change all three together.
 */
export function Brand({ href = "/", size = 26 }: { href?: string; size?: number }) {
  return (
    <Link href={href} className="flex items-center no-underline" style={{ color: "var(--ink)", gap: Math.round(size * 0.42) }}>
      <PrismMark size={size} />
      <span className="whitespace-nowrap font-record font-semibold leading-none tracking-[-0.01em]" style={{ fontSize: Math.round(size * 0.95) }}>
        <span className="font-normal" style={{ color: "var(--ink-3)" }}>read</span>Prism<span className="font-normal" style={{ color: "var(--ink-3)" }}>.news</span>
      </span>
    </Link>
  );
}
