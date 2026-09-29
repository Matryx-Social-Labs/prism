"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { SectionHead } from "@/components/SectionHead";
import { Checkbox } from "@/components/ui";
import { linkGoal } from "@/lib/attribution";
import { fetchWeeklyDigest, setWeeklyDigest, type Session } from "@/lib/session";

// The week's record by email (common/weekly_digest.py). Consent is this box and
// nothing else (DPDP s.6): unticked until the reader ticks it, never ticked for
// them by a link, and unticking it is the whole withdrawal. The landing's line
// arrives here as /account#digest, so the box is where the reader lands.
export function DigestToggle({ session }: { session: Session }) {
  const [on, setOn] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLElement>(null);

  useEffect(() => {
    let live = true;
    fetchWeeklyDigest(session)
      .then((v) => live && setOn(v))
      .catch(() => live && setError("Your email setting could not load. Reload the page to try again."));
    return () => {
      live = false;
    };
  }, [session]);

  useEffect(() => {
    if (on === null || window.location.hash !== "#digest") return;
    box.current?.scrollIntoView?.({ block: "start" });
    box.current?.querySelector("input")?.focus({ preventScroll: true });
  }, [on]);

  async function change(next: boolean) {
    setBusy(true);
    setError(null);
    try {
      const saved = await setWeeklyDigest(session, next);
      setOn(saved);
      if (saved) linkGoal("digest");
    } catch {
      setError("That did not save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="digest" ref={box} aria-labelledby="digest-title" className="grid scroll-mt-20 gap-1">
      <SectionHead id="digest-title" title="Email" />
      {on !== null && (
        <Checkbox
          checked={on}
          disabled={busy}
          onChange={change}
          hint={
            <>
              The week&rsquo;s records that two or more outlets reported, each with its count, and the week&rsquo;s corrections, to {session.email}. Off until you tick it; untick it here or use the one-click link in any copy to stop. See the <Link href="/privacy" className="underline underline-offset-[3px]">privacy policy</Link>.
            </>
          }
        >
          The week&rsquo;s record by email, Sunday morning (IST)
        </Checkbox>
      )}
      <p role="status" style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
        {busy ? "Saving…" : error}
      </p>
    </section>
  );
}
