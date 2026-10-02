"use client";

/**
 * What /trending leads with. A founder pins a story for a number of days: it
 * heads the list, ahead of the running stories, and stays listed while the pin
 * holds even if it goes quiet. Unpinning returns it to the list's own order.
 * Every pin and unpin is recorded against the founder (the audit log).
 *
 * The list is the pinned and running stories, then what /trending lists, in its
 * order; a search finds any served story by its headline.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminHead, AdminSection, Quiet, useAdmin } from "@/components/admin/AdminShell";
import { istClock } from "@/components/admin/AuditItem";
import { dayLabel } from "@/components/admin/charts/format";
import { Alert } from "@/components/ui";
import { fetchAdminStories, pinStory, unpinStory, type AdminStory } from "@/lib/admin";

const PIN_DAYS = [1, 3, 7, 14, 30];
const until = (iso: string) => `${dayLabel(iso)} ${istClock(iso)} IST`;

function state(s: AdminStory): string {
  if (s.pinned && s.pinned_until) return `Pinned until ${until(s.pinned_until)}`;
  if (s.running) return s.status === "active" ? "Running story · listed" : "Running story · not listed";
  return s.status === "active" ? "Listed" : "Not listed";
}

function Row({ story, onPin, onUnpin, busy }: {
  story: AdminStory; onPin: (days: number) => void; onUnpin: () => void; busy: boolean;
}) {
  const [days, setDays] = useState(7);
  return (
    <li className="grid gap-2 border-b py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center" style={{ borderColor: "var(--line)" }}>
      <div className="grid min-w-0 gap-1">
        <Link href={`/trending/${story.slug}`} className="underline-offset-4 hover:underline" style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>
          {story.label}
        </Link>
        <span className="p-count">
          {state(story)} · {story.developments} {story.developments === 1 ? "record" : "records"} · {story.source_count}{" "}
          {story.source_count === 1 ? "outlet" : "outlets"}
        </span>
      </div>
      {story.pinned ? (
        <button type="button" className="p-btn p-btn--secondary" disabled={busy} onClick={onUnpin}>
          Unpin
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor={`days-${story.slug}`}>Days to pin {story.label}</label>
          <select id={`days-${story.slug}`} className="p-input w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {PIN_DAYS.map((d) => (
              <option key={d} value={d}>{d === 1 ? "1 day" : `${d} days`}</option>
            ))}
          </select>
          <button type="button" className="p-btn p-btn--secondary" disabled={busy} onClick={() => onPin(days)}>
            Pin
          </button>
        </div>
      )}
    </li>
  );
}

export default function StoriesAdminPage() {
  const { session } = useAdmin();
  const [stories, setStories] = useState<AdminStory[] | null>(null);
  const [q, setQ] = useState("");
  const [searched, setSearched] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(
    (query: string) =>
      fetchAdminStories(session, query)
        .then((r) => setStories(r.stories))
        .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the stories")),
    [session],
  );

  useEffect(() => {
    void load(searched);
  }, [load, searched]);

  const act = async (slug: string, call: () => Promise<AdminStory>) => {
    setBusy(slug);
    setError("");
    try {
      await call();
      await load(searched);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change was refused");
    } finally {
      setBusy("");
    }
  };

  const pinned = stories?.filter((s) => s.pinned).length ?? 0;
  return (
    <>
      <AdminHead title="Stories" line={stories ? `${pinned} PINNED · ${stories.length} SHOWN` : null} />
      {error && <Alert tone="error">{error}</Alert>}
      <form
        className="flex flex-wrap gap-2"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setSearched(q);
        }}
      >
        <label className="sr-only" htmlFor="story-search">Find a story by its headline</label>
        <input id="story-search" className="p-input flex-[1_1_260px]" placeholder="Find a story by its headline" value={q} onChange={(e) => setQ(e.target.value)} />
        <button type="submit" className="p-btn p-btn--secondary">Find</button>
      </form>
      <AdminSection
        title={searched ? `Stories matching “${searched}”` : "What /trending leads with"}
        hint="A pinned story heads the list, ahead of the running stories, while the pin holds. Recorded in the audit log."
      >
        {stories && stories.length === 0 && <Quiet>No served story matches that.</Quiet>}
        <ul>
          {stories?.map((s) => (
            <Row
              key={s.slug}
              story={s}
              busy={busy === s.slug}
              onPin={(days) => void act(s.slug, () => pinStory(session, s.slug, days))}
              onUnpin={() => void act(s.slug, () => unpinStory(session, s.slug))}
            />
          ))}
        </ul>
      </AdminSection>
    </>
  );
}
