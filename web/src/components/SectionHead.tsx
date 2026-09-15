/** A section head in the structural voice, with the counted line beneath it in mono. */
export function SectionHead({ id, title, count, hint }: { id: string; title: string; count?: number; hint?: string }) {
  return (
    <div className="rule-live mb-4 pt-4">
      <h2 id={id} className="font-display text-[26px] font-medium uppercase leading-none tracking-[0.03em]">
        {title}
        {count != null && (
          <span className="ml-2 font-mono text-[11px] font-normal tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>
            {count}
          </span>
        )}
      </h2>
      {hint && (
        <p className="mt-1.5 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}

