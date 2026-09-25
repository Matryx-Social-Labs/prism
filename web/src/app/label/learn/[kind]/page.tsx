"use client";

/**
 * One task kind, taught: what it asks, DO / DO NOT, and worked examples — the
 * same guide a labeller meets before a batch, readable at leisure.
 *
 * Behind sign-in and an application (founder, 2026-09-23; decision G1): the
 * guide is fetched from the API for an account that has applied, and nobody
 * else receives it — not even in the page's JavaScript. A stranger is asked
 * to sign in; a signed-in reader who has not applied is sent to apply.
 */

import Link from "next/link";
import { notFound, useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import { SectionHead } from "@/components/SectionHead";
import { GuidePrimer } from "@/components/label/GuideView";
import { LabelStrip } from "@/components/label/parts";
import type { LabelGuide } from "@/lib/api";
import { LEARNABLE, fetchGuide } from "@/lib/labeller";
import { useSession } from "@/lib/session";

type State = "loading" | "signed-out" | "apply" | "error" | "ok";

export default function LearnTask({ params }: { params: Promise<{ kind: string }> }) {
  const { kind } = use(params);
  const router = useRouter();
  const session = useSession();
  // useSession reads storage in an effect, so its first value is null for everyone.
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<State>("loading");
  const [guide, setGuide] = useState<LabelGuide | null>(null);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted) return;
    if (!session) {
      setState("signed-out");
      return;
    }
    let live = true;
    fetchGuide(session, kind)
      .then((g) => {
        if (!live) return;
        setGuide(g);
        setState("ok");
      })
      .catch((e: unknown) => {
        if (!live) return;
        const status = (e as { status?: number }).status;
        setState(status === 401 ? "signed-out" : status === 403 ? "apply" : "error");
      });
    return () => {
      live = false;
    };
  }, [mounted, session, kind]);

  if (!LEARNABLE.includes(kind)) notFound();
  // The layout already provides <main>; this is the column.
  return (
    <div className="mx-auto grid min-h-dvh w-full max-w-[720px] content-start gap-8 px-4 pb-12 pt-6">
      <LabelStrip />
      {state === "ok" && guide && (
        <GuidePrimer guide={guide} onStart={() => router.push("/label")} action="Back to your workspace" />
      )}
      {state === "signed-out" && (
        <Gate text="The guides are for people who label for Prism. Sign in to read them.">
          <Link href={`/signin?next=/label/learn/${kind}`} className="p-btn p-btn--primary">
            Sign in
          </Link>
        </Gate>
      )}
      {state === "apply" && (
        <Gate text="The guides open once you have applied to label.">
          <Link href="/label" className="p-btn p-btn--primary">
            Apply to label
          </Link>
        </Gate>
      )}
      {state === "error" && <Gate text="The guide could not be loaded. Reload to try again." />}
    </div>
  );
}

function Gate({ text, children }: { text: string; children?: React.ReactNode }) {
  return (
    <div className="grid justify-items-start gap-4">
      <div className="w-full">
        <SectionHead id="h-label" as="h1" title="Label for Prism" />
        <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{text}</p>
      </div>
      {children}
    </div>
  );
}
