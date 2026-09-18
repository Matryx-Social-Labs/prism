/** A section title in the record voice, the count in mono beside it, an optional hint beneath. */
export function SectionHead({ id, title, count, hint, right }: { id: string; title: string; count?: number; hint?: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between gap-4 pb-3 pt-2">
      <div className="min-w-0">
        <h2 id={id} className="font-record text-[24px] font-medium leading-[1.2] tracking-[-0.01em]">
          {title}
          {count != null && (
            <span className="ml-2.5 align-middle font-mono text-[12px] font-normal tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
              {count}
            </span>
          )}
        </h2>
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
