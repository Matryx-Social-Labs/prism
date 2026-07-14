import { notFound } from "next/navigation";
import { fetchEvent, fetchQuestions } from "@/lib/api";
import { AskPanel } from "@/components/AskPanel";

export const dynamic = "force-dynamic";

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let event;
  let questions: string[] = [];
  try {
    [event, questions] = await Promise.all([fetchEvent(id), fetchQuestions(id)]);
  } catch {
    notFound();
  }
  if (!event) notFound();

  const cyber = event.projection?.cyber ?? null;
  const sourceById = new Map(event.sources.map((s) => [s.article_id, s]));

  return (
    <article className="space-y-8">
      {/* Header */}
      <header>
        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
          {cyber?.cvss?.score != null && (
            <span className="rounded bg-red-600 px-1.5 py-0.5 font-semibold text-white">
              CVSS {cyber.cvss.score.toFixed(1)} {cyber.cvss.severity ?? ""}
            </span>
          )}
          {cyber?.exploitation?.kev_listed && (
            <span className="rounded bg-red-700 px-1.5 py-0.5 font-semibold text-white">
              ⚠ CISA KEV — actively exploited
            </span>
          )}
          {(cyber?.cve_ids ?? []).map((cve) => (
            <span key={cve} className="rounded bg-stone-200 px-1.5 py-0.5 font-mono dark:bg-stone-800">
              {cve}
            </span>
          ))}
        </div>
        <h1 className="text-2xl font-bold leading-tight">{event.title}</h1>
        {event.summary && <p className="mt-2 text-stone-600 dark:text-stone-400">{event.summary}</p>}
      </header>

      {/* Both Sides */}
      <section>
        <h2 className="mb-3 text-lg font-bold">Both sides</h2>
        {event.perspectives.length === 0 ? (
          <p className="text-sm text-stone-500">Perspective analysis pending.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {event.perspectives.map((p, i) => (
              <div key={i} className="rounded-lg border border-stone-200 p-4 dark:border-stone-800">
                <div className="mb-1 flex items-center gap-2">
                  <span className="font-semibold">{p.label}</span>
                  {p.origin_country && (
                    <span className="rounded bg-stone-200 px-1 text-xs dark:bg-stone-800">{p.origin_country}</span>
                  )}
                  {p.stance && <span className="text-xs text-stone-500">{p.stance}</span>}
                </div>
                {p.summary && <p className="text-sm text-stone-600 dark:text-stone-400">{p.summary}</p>}
                <div className="mt-2 flex flex-wrap gap-1">
                  {p.article_ids.map((aid) => {
                    const src = sourceById.get(aid);
                    return src ? (
                      <span key={aid} className="rounded bg-stone-100 px-1.5 py-0.5 text-xs text-stone-600 dark:bg-stone-900 dark:text-stone-400">
                        {src.source_name}
                      </span>
                    ) : null;
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* So What */}
      <section>
        <h2 className="mb-3 text-lg font-bold">So what</h2>
        <div className="space-y-4">
          {event.impacts.length > 0 && (
            <ul className="space-y-2">
              {event.impacts.map((imp) => (
                <li key={imp.id} className={`flex items-start gap-2 text-sm ${imp.parent_impact_id ? "ml-6" : ""}`}>
                  <span className={imp.direction === "negative" ? "text-red-500" : imp.direction === "positive" ? "text-green-600" : "text-amber-500"}>
                    {imp.parent_impact_id ? "↳" : "●"}
                  </span>
                  <span>
                    <strong>{imp.entity_name ?? "Affected party"}</strong> — {imp.effect.replaceAll("_", " ")}
                    <span className="text-stone-400"> · {imp.horizon ?? "unknown horizon"}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}

          {cyber?.affected && cyber.affected.length > 0 && (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-stone-500">Affected products</h3>
              <ul className="text-sm">
                {cyber.affected.map((a, i) => (
                  <li key={i}>
                    {a.vendor} {a.product} {a.versions ? <span className="font-mono text-xs">({a.versions})</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {cyber?.remediation?.action && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950">
              <strong>Required action:</strong> {cyber.remediation.action}
            </div>
          )}

          {cyber?.control_mapping && cyber.control_mapping.length > 0 && (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-stone-500">For your controls</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-stone-200 text-xs uppercase text-stone-500 dark:border-stone-800">
                      <th className="py-1 pr-4">Framework</th>
                      <th className="py-1 pr-4">Control</th>
                      <th className="py-1">Why it matters here</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cyber.control_mapping.map((cm, i) => (
                      <tr key={i} className="border-b border-stone-100 dark:border-stone-900">
                        <td className="py-1.5 pr-4 font-mono text-xs">{cm.framework}</td>
                        <td className="py-1.5 pr-4 font-semibold">{cm.control}</td>
                        <td className="py-1.5 text-stone-600 dark:text-stone-400">{cm.relevance}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Sources */}
      <section>
        <h2 className="mb-3 text-lg font-bold">Sources ({event.sources.length})</h2>
        <ul className="space-y-1.5 text-sm">
          {event.sources.map((s) => (
            <li key={s.article_id} className="flex items-baseline gap-2">
              <span className="shrink-0 rounded bg-stone-200 px-1.5 py-0.5 text-xs dark:bg-stone-800">{s.source_name}</span>
              {s.url ? (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="truncate text-blue-700 hover:underline dark:text-blue-400">
                  {s.title}
                </a>
              ) : (
                <span className="truncate">{s.title}</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      {/* Ask */}
      <section>
        <h2 className="mb-3 text-lg font-bold">Ask this story</h2>
        <p className="mb-3 text-xs text-stone-500">
          Answers come only from this story&apos;s sources, with citations. The agent refuses questions the sources don&apos;t cover.
        </p>
        <AskPanel eventId={event.id} suggestedQuestions={questions} />
      </section>
    </article>
  );
}
