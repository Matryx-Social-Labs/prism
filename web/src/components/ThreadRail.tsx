"use client";

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

function Node({ node, arrow }: { node: ThreadNode; arrow: "up" | "down" }) {
  return (
    <li className="relative pl-7">
      <span
        aria-hidden
        className="absolute left-0 top-1 flex h-5 w-5 items-center justify-center rounded-full border text-[10px]"
        style={{ borderColor: "var(--line)", color: "var(--ink-faint)", background: "var(--bg-elevated)" }}
      >
        {arrow === "up" ? "↑" : "↓"}
      </span>
      <Link href={`/story/${node.event_id}`} className="group block">
        <span className="text-sm font-semibold leading-snug underline-offset-4 group-hover:underline">
          {node.title}
        </span>
        <span className="ml-2 text-xs" style={{ color: "var(--ink-faint)" }}>
          {node.sector}
          {node.occurred_at && ` · ${node.occurred_at.slice(0, 10)}`}
        </span>
      </Link>
      {node.rationale && (
        <p className="mt-0.5 text-xs leading-relaxed" style={{ color: "var(--ink-muted)" }}>
          {node.rationale}
        </p>
      )}
    </li>
  );
}

export function ThreadRail({
  thread,
  currentTitle,
}: {
  thread: { upstream: ThreadNode[]; downstream: ThreadNode[] };
  currentTitle: string;
}) {
  if (!thread || (thread.upstream.length === 0 && thread.downstream.length === 0)) return null;
  return (
    <section>
      <h2 className="mb-1.5 text-xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        The thread
      </h2>
      <p className="mb-4 text-xs" style={{ color: "var(--ink-faint)" }}>
        Connected stories Prism linked to this one — what led here and what followed.
      </p>
      <div
        className="relative rounded-2xl border p-5"
        style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
      >
        <span
          aria-hidden
          className="absolute bottom-5 left-[29px] top-5 w-px"
          style={{ background: "var(--line)" }}
        />
        <ol className="space-y-5">
          {thread.upstream.map((n) => (
            <Node key={n.event_id} node={n} arrow="up" />
          ))}
          <li className="relative pl-7">
            <span
              aria-hidden
              className="absolute left-0 top-1 flex h-5 w-5 items-center justify-center rounded-full text-[10px]"
              style={{ background: "var(--ink)", color: "var(--bg)" }}
            >
              ●
            </span>
            <span className="text-sm font-semibold" style={{ color: "var(--ink-muted)" }}>
              {currentTitle}
              <span className="ml-2 text-xs font-normal" style={{ color: "var(--ink-faint)" }}>
                (this story)
              </span>
            </span>
          </li>
          {thread.downstream.map((n) => (
            <Node key={n.event_id} node={n} arrow="down" />
          ))}
        </ol>
      </div>
    </section>
  );
}
