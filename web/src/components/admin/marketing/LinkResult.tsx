"use client";

/**
 * A link just made (/admin/marketing): the short address to post, the full
 * one with its tags, a post written from the page's own facts (edit it before
 * posting), the button that opens the platform with it, and the page's share
 * images — the link preview the platform will show, and Instagram's post and
 * Story shapes to download.
 */

import { useState } from "react";

import { TextField } from "@/components/ui";
import type { ShareLink } from "@/lib/admin";
import { type Facts, PLATFORM_LABEL, type Platform, X_LIMIT, cardImages, draft, label, shareUrl, xLength } from "@/lib/shareLinks";

function Copy({ text, what }: { text: string; what: string }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1600);
    } catch {
      /* no clipboard (an http origin): the text stays selectable */
    }
  };
  return (
    <button type="button" className="p-btn p-btn--secondary p-btn--sm p-hit" onClick={() => void copy()} aria-label={`Copy ${what}`}>
      {done ? "Copied" : "Copy"}
    </button>
  );
}

function Address({ name, url, what }: { name: string; url: string; what: string }) {
  return (
    <div className="grid gap-1">
      <span className="p-eyebrow">{name}</span>
      <div className="flex items-center gap-2">
        <code className="min-w-0 flex-1 select-all font-mono text-[12.5px] [overflow-wrap:anywhere]" style={{ color: "var(--ink)" }}>{url}</code>
        <Copy text={url} what={what} />
      </div>
    </div>
  );
}

export function LinkResult({ link, facts, platform }: { link: ShareLink; facts: Facts; platform: Platform }) {
  const [post, setPost] = useState(() => draft(facts, platform, link.short_url));
  const open = shareUrl(platform, link.short_url, post, label(facts));
  const images = cardImages(link.path);
  const name = PLATFORM_LABEL[platform];
  const x = platform === "x" ? xLength(post) : null;
  return (
    <div role="group" className="admin-panel grid gap-4" aria-label={`The ${name} link`}>
      <div className="grid gap-3 lg:grid-cols-2">
        <Address name="Post this" url={link.short_url} what="the short link" />
        <Address name="Or the full link, with its tags" url={link.url} what="the full link" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,300px)]">
        <div className="grid content-start gap-2">
          <TextField label={`The post for ${name}`} multiline rows={6} value={post} onChange={setPost}
            hint="Written from the page's own facts. Edit it before you post; keep every number as the page prints it." />
          {x !== null && (
            <p className="p-count" style={{ color: x > X_LIMIT ? "var(--danger)" : undefined }}>
              {x} of {X_LIMIT} characters, the link counted as 23{x > X_LIMIT ? " · too long for X" : ""}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {open && (
              <a className="p-btn p-btn--primary p-btn--sm p-hit" href={open} target="_blank" rel="noopener noreferrer">
                Open in {name}
              </a>
            )}
            <Copy text={post} what="the post" />
          </div>
          {platform === "instagram" && (
            <p className="text-[13.5px] leading-[1.45]" style={{ color: "var(--ink-2)" }}>
              Instagram does not make a link in a caption clickable. Put the short link in the bio, or on a Story&apos;s link sticker, and post one of the images.
            </p>
          )}
        </div>
        <figure className="grid content-start gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element -- the card route's own PNG, as the platform will fetch it */}
          <img src={images.preview} alt={`The link preview ${name} will show for ${label(facts)}`} width={1200} height={630}
            className="h-auto w-full border" style={{ borderColor: "var(--line)" }} />
          <figcaption className="grid gap-1 text-[13px]">
            <a className="p-link" href={images.preview} download={`prism-${link.code}-preview.png`}>Link preview · 1200 × 630</a>
            <a className="p-link" href={images.portrait} download={`prism-${link.code}-post.png`}>Instagram post · 1080 × 1350</a>
            <a className="p-link" href={images.story} download={`prism-${link.code}-story.png`}>Instagram Story · 1080 × 1920</a>
          </figcaption>
        </figure>
      </div>
    </div>
  );
}
