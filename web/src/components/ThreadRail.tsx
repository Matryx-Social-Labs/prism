"use client";

// The story thread: what led here → this story → what followed, as a
// dot timeline. Every linked event carries its cited rationale.

import Link from "next/link";

export interface ThreadNode {
  event_id: string;
  title: string;
  sector: string | null;
  occurred_at: string | null;
  relation: string;
  rationale: string | null;
  confidence: number | null;
  image_url: string | null;
}

interface Row {
  key: string;
  title: string;
  when: string;
  why: string | null;
  href: string | null;
  now: boolean;
}

function rows(thread: { upstream: ThreadNode[]; downstream: ThreadNode[] }, currentTitle: string): Row[] {
  const fmt = (n: ThreadNode) => (n.occurred_at ? n.occurred_at.slice(0, 10) : (n.sector ?? "related"));
  return [
    ...thread.upstream.map((n) => ({
      key: n.event_id,
      title: n.title,
      when: fmt(n),
      why: n.rationale,
      href: `/story/${n.event_id}`,
      now: false,
    })),
    { key: "__now", title: currentTitle, when: "This story", why: null, href: null, now: true },
    ...thread.downstream.map((n) => ({
      key: n.event_id,
      title: n.title,
      when: fmt(n),
      why: n.rationale,
      href: `/story/${n.event_id}`,
      now: false,
    })),
  ];
}

export function ThreadRail({
  thread,
  currentTitle,
}: {
  thread: { upstream: ThreadNode[]; downstream: ThreadNode[] };
  currentTitle: string;
}) {
  if (!thread || (thread.upstream.length === 0 && thread.downstream.length === 0)) return null;
  const list = rows(thread, currentTitle);
  return (
    <section className="mt-11">
      <h2 className="mb-1.5 text-[23px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        The thread
      </h2>
      <p className="mb-[18px] text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
        What led here, and what followed — each link carries its cited rationale.
      </p>
      <div className="flex flex-col">
        {list.map((row, i) => (
          <div key={row.key} className="flex gap-4">
            <div className="flex w-3.5 shrink-0 flex-col items-center">
              <span
                className="mt-[5px] shrink-0 rounded-full"
                style={{
                  width: row.now ? 12 : 9,
                  height: row.now ? 12 : 9,
                  background: row.now ? "var(--spectrum)" : "var(--line-strong)",
                }}
              />
              {i < list.length - 1 && <span className="min-h-[26px] w-0.5 flex-1" style={{ background: "var(--line)" }} />}
            </div>
            <div className="min-w-0 flex-1 pb-[22px]">
              <span
                className="text-[11px] font-semibold uppercase tracking-wide"
                style={{ color: row.now ? "var(--lens-general)" : "var(--ink-faint)" }}
              >
                {row.when}
              </span>
              {row.href ? (
                <Link
                  href={row.href}
                  className="mt-[3px] block text-sm font-semibold leading-[1.4]"
                  style={{ color: "var(--lens-cyber)" }}
                >
                  {row.title} →
                </Link>
              ) : (
                <p
                  className="mt-[3px] font-semibold leading-[1.4]"
                  style={{ fontSize: row.now ? "15.5px" : "14px", color: row.now ? "var(--ink)" : "var(--ink-muted)" }}
                >
                  {row.title}
                </p>
              )}
              {row.why && (
                <p className="mt-[5px] text-[12.5px] leading-[1.55]" style={{ color: "var(--ink-faint)" }}>
                  {row.why}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
