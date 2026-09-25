"use client";

import Link from "next/link";
import type { OutletRef, TrendingStory } from "@/lib/api";
import { CoverageBar, CoverageLegend } from "@/components/Coverage";
import { Reveal } from "@/components/Reveal";
import { StatusPill } from "@/components/StatusPill";
import { Ago } from "@/components/Ago";

// One outlet of each origin: the key's colours only. Nothing here prints a count.
const KEY: OutletRef[] = (["national", "intl", "regional"] as const).map((origin, i) => ({ slug: origin, publisher: origin, name: "", code: "", origin, language: i === 2 ? "hi" : "en" }));

const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

/**
 * The desk's right column (Pages v3 · Today, from xl): stories developing over
 * days — a different cut from the list — and how to read a record.
 */
export function TodayAside({ developing }: { developing: TrendingStory[] }) {
  return (
    <aside aria-label="Alongside today's record" className="hidden xl:sticky xl:top-[calc(var(--topbar)+24px)] xl:grid xl:content-start xl:gap-7 xl:self-start">
      {developing.length > 0 && (
        <section aria-labelledby="developing">
          <h2 id="developing" className="p-eyebrow pb-2" style={{ borderBottom: "var(--rule-section) solid var(--ink)" }}>Developing over days</h2>
          <ol>
            {developing.map((s, i) => (
              <li key={s.slug}>
                <Reveal delay={i * 60}>
                  <Link href={`/trending/${s.slug}`} className="group grid gap-1.5 border-b py-3" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
                    <span className="underline-offset-4 group-hover:underline" style={{ font: "var(--t-title-s)" }}>{s.hero_title ?? s.label}</span>
                    <span className="flex min-w-0 items-center gap-2">
                      {/* /trending carries no outlet origins, so the bar is drawn mono, never a guessed split. */}
                      <CoverageBar outlets={[]} fallbackCount={s.source_count} width={48} className="p-covbar--mono" />
                      <span className="p-count">
                        {plural(s.developments, "development")} · {plural(s.source_count, "outlet")}
                        {s.last_updated_at && <> · <Ago iso={s.last_updated_at} /></>}
                      </span>
                    </span>
                  </Link>
                </Reveal>
              </li>
            ))}
          </ol>
          <Link href="/trending" className="p-link mt-2.5 inline-block text-[13.5px]">All developing stories →</Link>
        </section>
      )}
      <section aria-labelledby="how-to-read" className="grid gap-2.5 p-4" style={{ background: "var(--sunken)" }}>
        <h2 id="how-to-read" className="p-eyebrow">How to read a record</h2>
        <CoverageBar outlets={KEY} size="lg" width={220} />
        <CoverageLegend outlets={KEY} withCounts={false} />
        <div className="flex flex-wrap gap-1.5">
          <StatusPill status="verified" />
          <StatusPill status="provisional" />
        </div>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>A dashed row has one source so far.</p>
      </section>
    </aside>
  );
}
