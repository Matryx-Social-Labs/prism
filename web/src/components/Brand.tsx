import Link from "next/link";
import { PrismMark } from "@/components/PrismMark";

/**
 * The wordmark lockup: the mark (the logo — unchanged) and "Prism" in the record
 * voice. Founder call 2026-09-18: the Teko wordmark was never part of the logo,
 * so the name is set in the same face as every headline. One treatment on every
 * surface; `href` is the only variable.
 */
export function Brand({ href = "/", size = 26, label = "Prism" }: { href?: string; size?: number; label?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2.5" style={{ color: "var(--ink)" }} aria-label={label}>
      <PrismMark size={size} />
      <span className="font-record font-semibold leading-none tracking-[-0.01em]" style={{ fontSize: Math.round(size * 0.92) }}>
        Prism
      </span>
    </Link>
  );
}
