/** Design System v2 · EmptyState (ui/EmptyState.jsx): a dashed box whose title
 *  names what is missing, an optional line on why, and at most one action. */
export function EmptyState({ title, children, action }: { title: React.ReactNode; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="grid gap-2 px-5 py-8" style={{ border: "1px dashed var(--line-strong)", borderRadius: "var(--r-lg)" }}>
      <p style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>{title}</p>
      {children && <p className="max-w-[52ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{children}</p>}
      {action && <div className="mt-1.5">{action}</div>}
    </div>
  );
}
