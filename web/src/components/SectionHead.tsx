/** A section head under the 3px ink rule, newspaper style (Design System v2 · SectionHead):
 *  the title in the record voice, a count in mono beside it, and beneath it either a
 *  provenance strip (`sub`, mono: "40 records · 21 outlets") or a prose `hint`.
 *  `as="h1"` for the head that names the page (Today, Stories): one h1 per page. */
export function SectionHead({ id, title, count, sub, hint, right, as: Tag = "h2" }: { id: string; title: string; count?: number; sub?: string; hint?: string; right?: React.ReactNode; as?: "h1" | "h2" }) {
  return (
    <div className="p-sechead">
      <div className="min-w-0">
        <Tag id={id} className="p-sechead__title">
          {title}
          {count != null && (
            <span className="ml-2.5 align-middle font-mono text-[13px] font-normal" style={{ color: "var(--ink-3)" }}>
              {count}
            </span>
          )}
        </Tag>
        {sub && <p className="p-sechead__sub">{sub}</p>}
        {hint && (
          <p className="mt-1 max-w-[56ch] text-[13.5px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
            {hint}
          </p>
        )}
      </div>
      {right}
    </div>
  );
}
