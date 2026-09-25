"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { useAsk } from "@/components/AskContext";
import type { EntityOut, SpeakerClaims } from "@/lib/api";
import { entityKind, markEntities, type Segment } from "@/lib/entities";

/**
 * Prose with the story's named entities marked (DESIGN.md § Entity marks).
 *
 * A mark is ink text with a thin accent underline — the record stays a record,
 * not a page of blue. Hover or focus (desktop) and tap (touch) open a small
 * card anchored to the mark: what kind of thing it is, what it said on this
 * story if it spoke, and one action — every story about it. The second tap on
 * touch follows that action; Escape and outside taps close the card. Text is
 * never altered: the mark wraps the words the article used.
 */
const CLOSE_MS = 120;
const CARD_W = 280;

export function EntityText({
  text,
  entities,
  claims = [],
  segments: given,
  as: Tag = "span",
  className,
  style,
}: {
  text: string;
  entities: EntityOut[];
  /** The story's quotes, so a person's card can say how much they said here. */
  claims?: SpeakerClaims[];
  /** Precomputed by markBlocks when this block is one of several in a passage. */
  segments?: Segment[];
  as?: "span" | "p";
  className?: string;
  style?: React.CSSProperties;
}) {
  const segments = given ?? markEntities(text, entities);
  return (
    <Tag className={className} style={style}>
      {segments.map((s, i) => (s.entity ? <EntityMark key={i} label={s.text} entity={s.entity} claims={claims} /> : <span key={i}>{s.text}</span>))}
    </Tag>
  );
}

const norm = (s: string) => s.replace(/\./g, " ").replace(/\s+/g, " ").trim().toLowerCase();

export function EntityMark({ label, entity, claims = [] }: { label: string; entity: EntityOut; claims?: SpeakerClaims[] }) {
  const ask = useAsk();
  const [open, setOpen] = useState(false);
  const id = useId();
  const wrap = useRef<HTMLSpanElement>(null);
  const timer = useRef<number | null>(null);
  const said = claims.find((sp) => norm(sp.speaker) === norm(entity.name));
  // The actor's page when the server has one (identity is the server's), else search.
  const href = entity.slug ? `/entity/${entity.slug}` : `/search?q=${encodeURIComponent(entity.name)}`;
  // The card opens under the mark, nudged left just enough to stay on screen.
  const [dx, setDx] = useState(0);
  const kind = entityKind(entity);

  const show = () => {
    if (timer.current) window.clearTimeout(timer.current);
    const r = wrap.current?.getBoundingClientRect();
    if (r) {
      const w = Math.min(CARD_W, window.innerWidth - 32);
      setDx(Math.max(16 - r.left, Math.min(0, window.innerWidth - 16 - w - r.left)));
    }
    setOpen(true);
  };
  const hide = () => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setOpen(false), CLOSE_MS);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onDown = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  return (
    <span ref={wrap} className="relative inline" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      <Link
        href={href}
        className="p-ent"
        aria-describedby={open ? id : undefined}
        onClick={(e) => {
          // On touch, the first tap opens the card; the card's own link follows.
          if (window.matchMedia("(hover: none)").matches && !open) {
            e.preventDefault();
            show();
          }
        }}
      >
        {label}
      </Link>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute top-[calc(100%+6px)] z-30 grid gap-2 p-3.5 text-left not-italic"
          style={{ left: dx, width: CARD_W, maxWidth: "calc(100vw - 32px)", background: "var(--elevated)", border: "1px solid var(--line-strong)", borderRadius: "var(--r-lg)", boxShadow: "var(--shadow-2)", font: "var(--t-body-s)", color: "var(--ink)", letterSpacing: 0 }}
        >
          <span className="grid gap-0.5">
            <b style={{ font: "var(--t-title-s)" }}>{entity.name}</b>
            <span className="text-[12.5px] font-medium leading-[1.3]" style={{ color: "var(--ink-3)" }}>
              {[kind, said?.role ?? (entity.role ? entity.role.replace(/_/g, " ") : null)].filter(Boolean).join(" · ")}
            </span>
          </span>
          {said && (
            <a href="#said" className="font-semibold" style={{ color: "var(--accent)" }} onClick={() => setOpen(false)}>
              Quoted {said.claims.length} {said.claims.length === 1 ? "time" : "times"} on this story ↓
            </a>
          )}
          {ask && (
            <button
              type="button"
              onClick={() => { setOpen(false); ask({ prefill: `What do the reports say about ${entity.name} on this story?`, via: "entity" }); }}
              className="text-left font-semibold"
              style={{ color: "var(--ink-2)" }}
            >
              Ask about {entity.name} on this story
            </button>
          )}
          <Link href={href} className="font-semibold" style={{ color: "var(--ink-2)" }}>
            All stories about {entity.name} →
          </Link>
        </span>
      )}
    </span>
  );
}
