import { ArrowDown, ArrowUp, Dash } from "@/components/icons";
import type { ImpactOut } from "@/lib/api";

/** The direction as the reports put it; an unknown direction gets no word. */
const WORD: Record<string, string> = { positive: "Up", negative: "Down", mixed: "Mixed" };

/**
 * Why it matters (Design System v2 · ImpactRow): who is affected, how, with a
 * direction and a horizon — each on a hairline, the arrow never alone (the
 * word sits under it). A follow-on effect hangs under the one it follows.
 */
export function Impacts({ impacts }: { impacts: ImpactOut[] }) {
  return (
    <ul>
      {impacts.map((imp) => {
        const word = imp.direction ? WORD[imp.direction] : undefined;
        return (
          <li
            key={imp.id}
            className={`grid grid-cols-[28px_minmax(0,1fr)] gap-2.5 border-t py-3 ${imp.parent_impact_id ? "ml-6 border-l pl-3" : ""}`}
            style={{ borderColor: "var(--line)" }}
          >
            <span className="grid justify-items-center gap-0.5 pt-0.5" style={{ color: "var(--ink)" }} aria-label={imp.direction ?? "direction unknown"}>
              {imp.direction === "negative" ? <ArrowDown size={16} /> : imp.direction === "positive" ? <ArrowUp size={16} /> : <Dash size={16} />}
              {word && <span className="font-mono text-[10px]" style={{ color: "var(--ink-3)" }} aria-hidden>{word}</span>}
            </span>
            <div className="grid min-w-0 gap-0.5">
              <b className="text-[14.5px] font-semibold leading-[1.35]">{imp.entity_name ?? "Affected party"}</b>
              <span style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{imp.effect.replaceAll("_", " ")}</span>
              {imp.horizon && <span className="p-count">{imp.horizon}</span>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
