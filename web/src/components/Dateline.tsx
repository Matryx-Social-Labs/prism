import { fetchFeed } from "@/lib/api";

// The masthead dateline. Every newspaper has one; no news app does. It states
// what the record currently holds, before a single word of marketing.
//
// The numbers are REAL — counted from the live feed — because this sits on a
// page whose entire claim is that every value traces to a source. Inventing
// "1,284 sources" here would undercut the product in its own header. If the API
// is unreachable we print the date alone rather than a fabricated count.
export async function Dateline() {
  let counts: string | null = null;
  try {
    const items = await fetchFeed({ limit: 200 });
    if (items.length) {
      const sources = items.reduce((n, i) => n + (i.source_count ?? 1), 0);
      const origins = new Set(items.flatMap((i) => i.regions ?? [])).size;
      counts =
        `${sources.toLocaleString("en-IN")} sources · ${items.length} stories` +
        (origins ? ` · ${origins} origins` : "");
    }
  } catch {
    /* no counts rather than invented ones */
  }

  const now = new Date();
  const full = now.toLocaleDateString("en-IN", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric",
  });
  // Phones drop the weekday and year — the line has to survive 390px.
  const short = now.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });

  return (
    <p
      className="font-mono text-[10px] uppercase tracking-[0.14em] sm:text-[10.5px] sm:tracking-[0.16em]"
      style={{ color: "var(--ink-faint)" }}
      suppressHydrationWarning
    >
      <span className="sm:hidden">{short}</span>
      <span className="hidden sm:inline">{full}</span>
      {counts ? ` · ${counts}` : ""}
    </p>
  );
}
