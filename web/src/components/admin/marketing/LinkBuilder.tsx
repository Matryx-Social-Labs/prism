"use client";

/**
 * Make a link (/admin/marketing): what to share — a pasted readprism.news
 * address, a story found by search, or one of today's — then the platform, and
 * a campaign to group it with others. What the page is and what the post will
 * say come from the page's own facts (lib/shareLinks.describe); the API checks
 * the page again and makes the code (api/routes/admin_marketing.py).
 */

import { useEffect, useId, useState } from "react";

import { useAdmin } from "@/components/admin/AdminShell";
import { Alert, SelectField, TextField } from "@/components/ui";
import { type LinksPayload, type ShareLink, makeLink } from "@/lib/admin";
import { type FeedItem, fetchFeed, searchEvents } from "@/lib/api";
import { type Facts, PLATFORM_LABEL, type Platform, describe, kindOf, label, targetPath } from "@/lib/shareLinks";

/** The pages a founder shares most, one tap each. */
const QUICK: ReadonlyArray<{ path: string; label: string }> = [
  { path: "/feed", label: "Today's record" },
  { path: "/", label: "Front page" },
  { path: "/plus", label: "Plus" },
  { path: "/state", label: "Every state" },
];
const PICKS = 6;
const SEARCH_FROM = 3;
/** A campaign as the API takes it: lowercase letters, digits and single hyphens. */
const campaignWord = (v: string) => v.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+/, "").slice(0, 32);

export function LinkBuilder({ data, onMade }: { data: LinksPayload; onMade: (link: ShareLink, facts: Facts, platform: Platform) => void }) {
  const { session } = useAdmin();
  const campaignsId = useId();
  const [input, setInput] = useState("");
  // null while reading; "missing" when there is no such page to link to.
  const [facts, setFacts] = useState<Facts | "missing" | null>(null);
  const [reading, setReading] = useState(false);
  const [query, setQuery] = useState("");
  const [picks, setPicks] = useState<FeedItem[] | null>(null);
  const [platform, setPlatform] = useState<Platform>("whatsapp");
  const [medium, setMedium] = useState(data.platforms.whatsapp ?? "message");
  const [campaign, setCampaign] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const path = targetPath(input, typeof window === "undefined" ? undefined : window.location.host);

  // Today's stories, or what a search finds: one tap puts a story in the field.
  useEffect(() => {
    let live = true;
    const q = query.trim();
    const load = q.length >= SEARCH_FROM ? searchEvents(q).then((found) => found.items) : fetchFeed({ sort: "top", limit: PICKS });
    load.then((items) => live && setPicks(items.slice(0, PICKS))).catch(() => live && setPicks([]));
    return () => {
      live = false;
    };
  }, [query]);

  // What the page is, read from the same API it is built from.
  useEffect(() => {
    setFacts(null);
    if (!path) return;
    let live = true;
    setReading(true);
    describe(path)
      .then((f) => live && setFacts(f ?? "missing"))
      .catch(() => live && setFacts("missing"))
      .finally(() => live && setReading(false));
    return () => {
      live = false;
    };
  }, [path]);

  const pickPlatform = (p: Platform) => {
    setPlatform(p);
    setMedium(data.platforms[p] ?? "social");
  };

  const ready = facts !== null && facts !== "missing" ? facts : null;
  const make = async () => {
    if (!path || !ready) return;
    setBusy(true);
    setError("");
    try {
      const link = await makeLink(session, { target: path, platform, medium, campaign: campaign.replace(/-+$/, ""), title: label(ready), note });
      onMade(link, ready, platform);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The link was not made. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const bad = input.trim() !== "" && !path;
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-8">
      <div className="grid content-start gap-3">
        <h3 className="p-eyebrow">1 · What to share</h3>
        <TextField
          label="A Prism page"
          placeholder="readprism.news/story/… or /state/kerala"
          value={input}
          onChange={setInput}
          error={bad ? "That is not a public Prism page. Paste a readprism.news address or a path such as /story/…" : undefined}
          hint={path ? `${kindOf(path)} · ${path}` : "A story, a quote, a person, a state, a day, or any public page."}
        />
        <div role="group" className="flex flex-wrap gap-1.5" aria-label="Quick picks">
          {QUICK.map((q) => (
            <button key={q.path} type="button" className="p-chip" aria-pressed={path === q.path} onClick={() => setInput(q.path)}>
              {q.label}
            </button>
          ))}
        </div>
        <TextField type="search" label="Find a story" placeholder="Search Prism's records" value={query} onChange={setQuery} />
        <ul className="grid" aria-label={query.trim().length >= SEARCH_FROM ? "Stories found" : "Today's top stories"}>
          {picks === null && <li className="py-2 text-[13.5px]" style={{ color: "var(--ink-3)" }}>Reading…</li>}
          {picks?.length === 0 && <li className="py-2 text-[13.5px]" style={{ color: "var(--ink-3)" }}>Nothing found.</li>}
          {picks?.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="admin-pick"
                aria-pressed={path === `/story/${item.id}`}
                onClick={() => setInput(`/story/${item.id}`)}
              >
                <span className="min-w-0 flex-1">{item.title}</span>
                <span className="font-mono text-[11.5px] tabular-nums" style={{ color: "var(--ink-3)" }}>
                  {item.source_count} {item.source_count === 1 ? "outlet" : "outlets"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid content-start gap-3">
        <h3 className="p-eyebrow">2 · Where it goes</h3>
        <div role="radiogroup" aria-label="Platform" className="flex flex-wrap gap-1.5">
          {(Object.keys(PLATFORM_LABEL) as Platform[]).filter((p) => p in data.platforms).map((p) => (
            <button key={p} type="button" role="radio" aria-checked={platform === p} className="p-chip" onClick={() => pickPlatform(p)}>
              {PLATFORM_LABEL[p]}
            </button>
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectField label="Medium" value={medium} onChange={setMedium} options={data.media.map((m) => ({ value: m, label: m }))} />
          <div>
            <TextField
              label="Campaign"
              placeholder="launch-week"
              value={campaign}
              onChange={(v) => setCampaign(campaignWord(v))}
              hint="Optional. Groups links: lowercase, hyphens."
              list={campaignsId}
            />
            <datalist id={campaignsId}>
              {data.campaigns.map((c) => <option key={c} value={c} />)}
            </datalist>
          </div>
        </div>
        <TextField label="Note" placeholder="Where you will post it, for your own list" value={note} onChange={setNote} maxLength={200} />
        <div className="admin-panel grid gap-1 text-[13.5px]" aria-live="polite">
          <span className="p-eyebrow">This link opens</span>
          {!path ? (
            <span style={{ color: "var(--ink-3)" }}>Pick a page first.</span>
          ) : reading || facts === null ? (
            <span style={{ color: "var(--ink-3)" }}>Reading the page…</span>
          ) : facts === "missing" ? (
            <span style={{ color: "var(--danger)" }}>No such page, or it could not be read. Check the address: a link to it would open an error.</span>
          ) : (
            <span className="font-semibold" style={{ color: "var(--ink)" }}>{label(facts)}</span>
          )}
        </div>
        {error && <Alert tone="error">{error}</Alert>}
        <button type="button" className="p-btn p-btn--primary p-btn--lg" disabled={!path || !ready || busy} onClick={() => void make()}>
          {busy ? "Making the link…" : `Make the ${PLATFORM_LABEL[platform]} link`}
        </button>
      </div>
    </div>
  );
}
