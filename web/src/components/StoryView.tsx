"use client";

import { useEffect, useState } from "react";
import { fetchBrief, fetchQuestions, type EventDetail } from "@/lib/api";
import { LENS_ORDER, lensMeta } from "@/lib/lenses";
import { loadProfile } from "@/lib/profile";
import { AskPanel } from "@/components/AskPanel";

export function StoryView({ event }: { event: EventDetail }) {
  const cyber = event.projection?.cyber ?? null;
  const finance = event.projection?.finance ?? null;
  const sourceById = new Map(event.sources.map((s) => [s.article_id, s]));

  const [lens, setLens] = useState("general");
  const [briefs, setBriefs] = useState<Record<string, string>>(event.lens_briefs ?? {});
  const [briefLoading, setBriefLoading] = useState(false);
  const [questions, setQuestions] = useState<string[]>([]);

  // Default to the reader's own lens once the profile is readable.
  useEffect(() => {
    const profile = loadProfile();
    const preferred = profile?.lens && LENS_ORDER.includes(profile.lens) ? profile.lens : "general";
    setLens(preferred);
  }, []);

  // Lens switch: pull the brief (generating+caching server-side if new)
  // and the lens-tuned suggested questions.
  useEffect(() => {
    let cancelled = false;
    fetchQuestions(event.id, lens).then((qs) => !cancelled && setQuestions(qs));
    if (!briefs[lens]) {
      setBriefLoading(true);
      fetchBrief(event.id, lens).then((res) => {
        if (cancelled) return;
        setBriefLoading(false);
        if (res?.brief) setBriefs((prev) => ({ ...prev, [lens]: res.brief! }));
      });
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lens, event.id]);

  const meta = lensMeta(lens);
  const brief = briefs[lens];

  return (
    <article className="space-y-10">
      {/* Header */}
      <header>
        <div className="mb-2.5 flex flex-wrap items-center gap-2 text-xs">
          {event.sector && (
            <span className="rounded-full px-2 py-0.5 font-semibold uppercase tracking-wide" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
              {event.sector}
            </span>
          )}
          {cyber?.cvss?.score != null && (
            <span className="rounded-full px-2 py-0.5 font-semibold" style={{ background: "var(--danger-bg)", color: "var(--danger)" }}>
              CVSS {cyber.cvss.score.toFixed(1)} {cyber.cvss.severity ?? ""}
            </span>
          )}
          {cyber?.exploitation?.kev_listed && (
            <span className="rounded-full px-2 py-0.5 font-semibold" style={{ background: "var(--danger)", color: "#fff" }}>
              ⚠ Actively exploited
            </span>
          )}
          {(cyber?.cve_ids ?? []).slice(0, 3).map((cve) => (
            <span key={cve} className="rounded-full px-2 py-0.5 font-mono" style={{ background: "var(--bg-sunken)" }}>
              {cve}
            </span>
          ))}
          {(finance?.tickers ?? []).slice(0, 4).map((t) => (
            <span key={t} className="rounded-full px-2 py-0.5 font-mono font-semibold" style={{ background: "var(--lens-finance-bg)", color: "var(--lens-finance)" }}>
              ${t}
            </span>
          ))}
          <span className="ml-auto" style={{ color: "var(--ink-faint)" }}>
            {event.sources.length} source{event.sources.length === 1 ? "" : "s"}
            {event.regions.length > 0 && ` · ${event.regions.join(", ")}`}
          </span>
        </div>
        <h1 className="text-3xl font-semibold leading-tight tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          {event.title}
        </h1>
        {event.summary && (
          <p className="mt-3 text-[15px] leading-relaxed" style={{ color: "var(--ink-muted)" }}>
            {event.summary}
          </p>
        )}
      </header>

      {/* Lens switcher + brief — the product moment */}
      <section
        className="overflow-hidden rounded-2xl border"
        style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-card)" }}
      >
        <div className="flex flex-wrap items-center gap-1.5 border-b px-4 py-3" style={{ borderColor: "var(--line)" }} role="tablist" aria-label="Read this story through a lens">
          <span className="mr-1 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-faint)" }}>
            Lens
          </span>
          {LENS_ORDER.map((slug) => {
            const m = lensMeta(slug);
            const selected = slug === lens;
            return (
              <button
                key={slug}
                role="tab"
                aria-selected={selected}
                onClick={() => setLens(slug)}
                className="rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
                style={
                  selected
                    ? { background: m.bg, color: m.color, boxShadow: `inset 0 0 0 1.5px ${m.color}` }
                    : { color: "var(--ink-muted)" }
                }
              >
                {m.name}
              </button>
            );
          })}
        </div>

        <div key={lens} className="fade-swap space-y-5 p-5">
          {/* Brief */}
          {brief ? (
            <p className="text-[15px] leading-relaxed">
              <span className="font-semibold" style={{ color: meta.color }}>
                Through the {meta.name} lens —{" "}
              </span>
              <span style={{ color: "var(--ink-muted)" }}>{brief}</span>
            </p>
          ) : briefLoading ? (
            <div className="space-y-2" aria-label="Generating lens brief">
              <div className="h-3.5 w-full animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
              <div className="h-3.5 w-11/12 animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
              <div className="h-3.5 w-4/5 animate-pulse rounded" style={{ background: "var(--bg-sunken)" }} />
              <p className="pt-1 text-xs" style={{ color: "var(--ink-faint)" }}>
                Writing the {meta.short} read of this story…
              </p>
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--ink-faint)" }}>
              No {meta.short} read available for this story yet.
            </p>
          )}

          {/* Lens-specific structured blocks */}
          {lens === "cyber_grc" && cyber && (
            <div className="space-y-4">
              {cyber.affected && cyber.affected.length > 0 && (
                <div>
                  <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--ink-faint)" }}>
                    Affected products
                  </h3>
                  <ul className="text-sm" style={{ color: "var(--ink-muted)" }}>
                    {cyber.affected.slice(0, 6).map((a, i) => (
                      <li key={i}>
                        {a.vendor} {a.product}{" "}
                        {a.versions && <span className="font-mono text-xs">({a.versions})</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {cyber.remediation?.action && (
                <div className="rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "var(--lens-cyber)", background: "var(--lens-cyber-bg)" }}>
                  <strong>Required action:</strong> {cyber.remediation.action}
                </div>
              )}
              {cyber.control_mapping && cyber.control_mapping.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b text-xs uppercase tracking-wide" style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}>
                        <th className="py-1.5 pr-4">Framework</th>
                        <th className="py-1.5 pr-4">Control</th>
                        <th className="py-1.5">Why it matters here</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cyber.control_mapping.map((cm, i) => (
                        <tr key={i} className="border-b" style={{ borderColor: "var(--line)" }}>
                          <td className="py-2 pr-4 font-mono text-xs">{cm.framework}</td>
                          <td className="py-2 pr-4 font-semibold">{cm.control}</td>
                          <td className="py-2" style={{ color: "var(--ink-muted)" }}>{cm.relevance}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {lens === "finance_trader" && finance && (finance.tickers?.length || finance.price_impact || finance.catalyst) ? (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "var(--lens-finance)", background: "var(--lens-finance-bg)" }}>
              {finance.tickers && finance.tickers.length > 0 && (
                <span><strong>Tickers:</strong> {finance.tickers.map((t) => `$${t}`).join(", ")}</span>
              )}
              {finance.sector && <span><strong>Sector:</strong> {finance.sector}</span>}
              {finance.catalyst && <span><strong>Catalyst:</strong> {finance.catalyst.replaceAll("_", " ")}</span>}
              {finance.price_impact?.direction && (
                <span>
                  <strong>Price read:</strong>{" "}
                  {finance.price_impact.direction === "up" ? "▲" : finance.price_impact.direction === "down" ? "▼" : "◆"}{" "}
                  {finance.price_impact.magnitude ?? ""}
                  {finance.price_impact.confidence != null && ` (${(finance.price_impact.confidence * 100).toFixed(0)}% conf.)`}
                </span>
              )}
            </div>
          ) : null}
        </div>
      </section>

      {/* Both Sides */}
      <section>
        <h2 className="mb-4 text-xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          Both sides
        </h2>
        {event.perspectives.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--ink-faint)" }}>Perspective analysis pending.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {event.perspectives.map((p, i) => (
              <div key={i} className="card-hover rounded-2xl border p-5" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="font-semibold">{p.label}</span>
                  {p.origin_country && (
                    <span className="rounded-full px-1.5 py-0.5 text-xs" style={{ background: "var(--bg-sunken)" }}>{p.origin_country}</span>
                  )}
                  {p.stance && <span className="text-xs" style={{ color: "var(--ink-faint)" }}>{p.stance}</span>}
                </div>
                {p.summary && <p className="text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>{p.summary}</p>}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {p.article_ids.map((aid) => {
                    const src = sourceById.get(aid);
                    return src ? (
                      <span key={aid} className="rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
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

      {/* So What — consequence graph */}
      <section>
        <h2 className="mb-4 text-xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          So what
        </h2>
        {event.impacts.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--ink-faint)" }}>Impact analysis pending.</p>
        ) : (
          <ul className="space-y-2.5">
            {event.impacts.map((imp) => (
              <li key={imp.id} className={`flex items-start gap-2.5 text-sm ${imp.parent_impact_id ? "ml-7" : ""}`}>
                <span aria-hidden style={{ color: imp.direction === "negative" ? "var(--danger)" : imp.direction === "positive" ? "var(--up)" : "var(--lens-general)" }}>
                  {imp.parent_impact_id ? "↳" : "●"}
                </span>
                <span>
                  <strong>{imp.entity_name ?? "Affected party"}</strong>{" "}
                  <span style={{ color: "var(--ink-muted)" }}>— {imp.effect.replaceAll("_", " ")}</span>
                  <span style={{ color: "var(--ink-faint)" }}> · {imp.horizon ?? "unknown horizon"}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Sources */}
      <section>
        <h2 className="mb-4 text-xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          Sources <span className="text-base font-normal" style={{ color: "var(--ink-faint)" }}>({event.sources.length})</span>
        </h2>
        <ul className="space-y-2 text-sm">
          {event.sources.map((s) => (
            <li key={s.article_id} className="flex items-baseline gap-2.5">
              <span className="shrink-0 rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
                {s.source_name}
              </span>
              {s.url ? (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="truncate underline-offset-4 hover:underline" style={{ color: "var(--lens-cyber)" }}>
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
        <h2 className="mb-1.5 text-xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
          Ask this story
        </h2>
        <p className="mb-4 text-xs" style={{ color: "var(--ink-faint)" }}>
          Answers come only from this story&apos;s sources, with citations. The agent refuses questions the sources don&apos;t cover.
        </p>
        <AskPanel eventId={event.id} suggestedQuestions={questions} />
      </section>
    </article>
  );
}
