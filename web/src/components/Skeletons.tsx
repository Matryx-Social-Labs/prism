// Skeletons in the exact geometry of what they stand in for (DESIGN.md
// § Empty, loading, error: `sunken` bars in the row's shape, never a
// spinner). One set, so Today, Stories, a record and a story load the same way.
const bar = (w: string | number, h = 12, extra = "") => (
  <span className={`pulse-skel block rounded ${extra}`} style={{ background: "var(--sunken)", width: w, height: h }} aria-hidden />
);

/** A story row with its thumbnail (Today, Search, Watchlist). */
export function RowSkeleton({ lead = false, i = 0 }: { lead?: boolean; i?: number }) {
  const widths = ["82%", "68%", "74%", "57%", "70%", "63%"];
  return (
    <div className={`row-card ${lead ? "px-[18px] py-5" : "px-4 py-3.5"} flex items-start gap-3.5`} aria-hidden>
      <span className={`pulse-skel shrink-0 rounded-[8px] ${lead ? "hidden" : "h-[76px] w-[104px] sm:h-[84px] sm:w-[124px]"}`} style={{ background: "var(--sunken)" }} />
      <div className="min-w-0 flex-1">
        {bar(96, 10)}
        {bar(widths[i % widths.length], lead ? 26 : 16, "mt-3")}
        {bar("90%", 12, "mt-2")}
        {!lead && bar("60%", 12, "mt-1.5")}
        <span className="mt-4 flex items-center gap-3">{bar(72, 6)}{bar(80, 10)}</span>
      </div>
    </div>
  );
}

/** A list of rows, in the grid Today uses on a wide desk. */
export function RowListSkeleton({ n = 6, label = "Loading" }: { n?: number; label?: string }) {
  return (
    <div className="grid grid-cols-1 gap-3 2xl:grid-cols-2" aria-busy="true" aria-label={label} role="status">
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className={i === 0 ? "2xl:col-span-2" : undefined}><RowSkeleton lead={i === 0} i={i} /></div>
      ))}
    </div>
  );
}
