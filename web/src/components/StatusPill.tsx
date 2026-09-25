import { Check } from "@/components/icons";

export type RecordStatus = "verified" | "provisional" | "single" | "corrected" | "disputed";

const LABEL: Record<RecordStatus, string> = {
  verified: "Verified record",
  provisional: "Provisional grouping",
  single: "One source so far",
  corrected: "Corrected",
  disputed: "Disputed",
};

/**
 * Honesty as UI (DESIGN.md § Status): verified is ink — the default, not an
 * alarm; provisional is dashed; corrected and disputed carry their hue.
 */
export function StatusPill({ status, label, title }: { status: RecordStatus; label?: string; title?: string }) {
  return (
    <span className={`status status-${status}`} title={title}>
      {status === "verified" && <Check />}
      {label ?? LABEL[status]}
    </span>
  );
}
