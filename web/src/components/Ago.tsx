import { relativeTime } from "@/lib/dateline";

/**
 * "12m ago" as a <time>. A cached page is rendered minutes before the browser
 * hydrates it, so the server's "25m ago" and the reader's "24m ago" legitimately
 * differ: the mismatch is expected, and React is told so for this one node
 * (otherwise it throws the tree away and re-renders it on the client).
 */
export function Ago({ iso, className, style }: { iso: string; className?: string; style?: React.CSSProperties }) {
  return (
    <time dateTime={iso} className={className} style={style} suppressHydrationWarning>
      {relativeTime(iso)}
    </time>
  );
}
