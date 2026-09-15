import type { SpeakerClaims } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

/**
 * The passenger list: who said what, verbatim, grouped by speaker.
 *
 * The quote and the speaker are the body voice; only the provenance line
 * ([n] · outlet · date) is mono. Nothing here is lens-coloured and nothing
 * here is unverified: every quote was checked against its article at write
 * time, and the model's stance never reaches the payload. `sourceIndex` is
 * the ONE index the sources list also uses, so the two can never number one
 * article differently.
 */
export function Said({
  claims,
  sourceIndex,
}: {
  claims: SpeakerClaims[];
  sourceIndex: Map<string, number>;
}) {
  return (
    <div className="flex flex-col">
      {claims.map((sp, i) => (
        <div
          key={sp.speaker}
          className={i === 0 ? "" : "mt-5 border-t pt-5"}
          style={i === 0 ? undefined : { borderColor: "var(--line)" }}
        >
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-[14.5px] font-semibold">{sp.speaker}</h3>
            <span
              className="shrink-0 text-[12.5px]"
              style={{ color: "var(--ink-faint)" }}
            >
              {sp.claims.length} {sp.claims.length === 1 ? "quote" : "quotes"}
            </span>
          </div>
          <ul className="mt-2 flex flex-col gap-3.5">
            {sp.claims.map((c, j) => {
              const n = sourceIndex.get(c.article_id);
              return (
                <li key={`${c.article_id}-${j}`}>
                  <blockquote
                    className="text-[14.5px] leading-[1.6]"
                    style={{ color: "var(--ink)" }}
                  >
                    “{c.quote_text}”
                  </blockquote>
                  <div
                    className="mt-1 flex items-baseline gap-2 font-mono text-[10.5px]"
                    style={{ color: "var(--ink-faint)" }}
                  >
                    {/* The citation IS the link: one tap to check us, same target/rel as
                          Sources. A 10.5px mono glyph is a 19x16 target, so the pseudo-element
                          grows the hit area to ~47x44 without moving the glyph or the line. */}
                    {n != null &&
                      (c.url ? (
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Source ${n}: ${c.source_name}`}
                          className="relative font-mono underline-offset-2 before:absolute before:-inset-3.5 before:content-[''] hover:underline"
                        >
                          [{n}]
                        </a>
                      ) : (
                        <span>[{n}]</span>
                      ))}
                    <span>{c.source_name}</span>
                    {c.published_at && (
                      <span>· {shortDate(c.published_at)}</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
