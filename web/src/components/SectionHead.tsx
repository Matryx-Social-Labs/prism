/** A section title in the record voice, the count in mono beside it, an optional hint beneath.
 *  `as="h1"` for the head that names the page (Today, Stories): one h1 per page, same size. */
export function SectionHead({ id, title, count, hint, right, as: Tag = "h2" }: { id: string; title: string; count?: number; hint?: string; right?: React.ReactNode; as?: "h1" | "h2" }) {
  return (
    <div className="section-head grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4 pb-3 pt-2">
      <div className="min-w-0">
        <Tag id={id} className="font-record text-[24px] font-bold leading-[1.24]">
          {title}
          {count != null && (
            <span className="ml-2.5 align-middle font-mono text-[12px] font-normal tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
              {count}
            </span>
          )}
        </Tag>
        {hint && (
          <p className="mt-1 max-w-[52ch] text-[13.5px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
            {hint}
          </p>
        )}
      </div>
      {right}
    </div>
  );
}
