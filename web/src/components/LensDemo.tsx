"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { lensMeta, useLenses } from "@/lib/lenses";

interface DemoStory {
  id: string | null; // null = curated example
  title: string;
  briefs: Record<string, string>;
}

// Curated example so the landing always shows the moment, even offline.
// Live multi-lens stories replace it when the API has one cached.
const CURATED: DemoStory = {
  id: null,
  title: "Armed conflict escalates along disputed border after failed ceasefire talks",
  briefs: {
    reader:
      "Fighting resumed overnight after mediated negotiations collapsed, displacing tens of thousands of residents near the border. Both governments blame each other for the breakdown, and aid agencies warn of a worsening humanitarian situation. Watch for emergency talks called by regional powers this week.",
    cyber:
      "Armed conflicts of this kind are historically followed by surges in state-aligned cyber activity: expect elevated phishing, DDoS, and wiper risk for government, energy, logistics, and media organizations operating in or near the involved regions. Defenders at organizations with suppliers or infrastructure in the area should review geo-blocking, patch cadence on internet-facing systems, and incident response readiness.",
    markets:
      "Markets typically price regional conflict through energy, defense, and insurance channels: watch crude and gas futures, defense primes, and shipping/war-risk insurance rates. Local-currency assets and neighboring-market ETFs face pressure while safe havens (gold, USD, treasuries) usually catch a bid. Key signal to watch: any disruption to physical trade routes or pipelines.",
  },
};

export function LensDemo() {
  const [story, setStory] = useState<DemoStory>(CURATED);
  const [active, setActive] = useState("reader");
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    // Look for a real story that already has 2+ cached briefs (never
    // trigger generation from the landing page).
    (async () => {
      try {
        const feed = await fetch(`${API_URL}/api/v1/feed?lens=reader&limit=8`).then((r) => r.json());
        for (const item of feed.items ?? []) {
          const detail = await fetch(`${API_URL}/api/v1/events/${item.id}`).then((r) => r.json());
          const briefs = detail.lens_briefs ?? {};
          if (Object.keys(briefs).length >= 2) {
            setStory({ id: item.id, title: detail.title, briefs });
            return;
          }
        }
      } catch {
        /* keep curated */
      }
    })();
  }, []);

  const registry = useLenses();
  const lenses = registry.map((m) => m.slug).filter((slug) => story.briefs[slug]);
  const meta = lensMeta(active);
  const brief = story.briefs[active] ?? story.briefs[lenses[0]];

  return (
    <div
      className="overflow-hidden rounded-2xl border"
      style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-center justify-between gap-3 border-b px-5 py-3" style={{ borderColor: "var(--line)" }}>
        <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: "var(--ink-faint)" }}>
          Try it — flip the lens
        </span>
        <span className="spectrum-bar h-1 w-16 rounded-full" aria-hidden />
      </div>

      <div className="px-5 pt-4">
        <h3 className="text-lg font-semibold leading-snug" style={{ fontFamily: "var(--font-display), serif" }}>
          {story.title}
        </h3>
      </div>

      <div className="flex gap-1.5 px-5 pt-4" role="tablist" aria-label="Lens">
        {lenses.map((slug) => {
          const m = lensMeta(slug);
          const selected = slug === active;
          return (
            <button
              key={slug}
              role="tab"
              aria-selected={selected}
              onClick={() => { setFlipped(true); setActive(slug); }}
              className="rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
              style={
                selected
                  ? { background: m.bg, color: m.color, boxShadow: `inset 0 0 0 1.5px ${m.color}` }
                  : { color: "var(--ink-muted)" }
              }
            >
              {m.short}
            </button>
          );
        })}
      </div>

      <div key={active} className={`${flipped ? "flip-body" : ""} relative overflow-hidden px-5 pb-5 pt-3`}>
          {flipped && <span aria-hidden className="flip-scanline" style={{ background: meta.color }} />}
        <p className="text-[15px] leading-relaxed" style={{ color: "var(--ink-muted)" }}>
          <span className="font-semibold" style={{ color: meta.color }}>
            Through the {meta.short} lens —{" "}
          </span>
          {brief}
        </p>
        {story.id && (
          <Link
            href={`/story/${story.id}`}
            className="mt-3 inline-block text-xs font-semibold underline-offset-4 hover:underline"
            style={{ color: meta.color }}
          >
            Open the full story →
          </Link>
        )}
      </div>
    </div>
  );
}
