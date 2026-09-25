"use client";

/**
 * One task kind, taught: what it asks, DO / DO NOT, and worked examples — the
 * same guide a labeller meets before a batch, readable at leisure.
 *
 * Behind sign-in and an application (founder, 2026-09-23; decision G1): the
 * guide is fetched from the API for an account that has applied, and nobody
 * else receives it — not even in the page's JavaScript. A stranger is asked
 * to sign in; a signed-in reader who has not applied is sent to apply.
 *
 * Design System v2 · Label board, "The guide": the kind as its provenance line,
 * the question as the title; loading as bars in the guide's shape; a failure in
 * words with another try and the way back.
 */

import Link from "next/link";
import { notFound, useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import { GuideFailed, GuideLoading, GuidePrimer } from "@/components/label/GuideView";
import { Column, LabelStrip, Lede, Title } from "@/components/label/parts";
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
  const [attempt, setAttempt] = useState(0);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted) return;
    if (!session) {
      setState("signed-out");
      return;
    }
    let live = true;
    setState("loading");
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
  }, [mounted, session, kind, attempt]);

  if (!LEARNABLE.includes(kind)) notFound();
  // The layout already provides <main>; this is the label bar and the column.
  return (
    <div className="flex min-h-dvh w-full flex-col">
      <LabelStrip email={session?.email} />
      <Column>
        {state === "loading" && mounted && <GuideLoading />}
        {state === "ok" && guide && (
          <GuidePrimer
            guide={guide}
            context={<p className="p-count">Guide · {kind}</p>}
            onStart={() => router.push("/label")}
            action="Back to your workspace"
          />
        )}
        {state === "signed-out" && (
          <Gate text="The guides are for people who label for Prism. Sign in to read them.">
            <Link href={`/signin?next=/label/learn/${kind}`} className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto">
              Sign in
            </Link>
          </Gate>
        )}
        {state === "apply" && (
          <Gate text="The guides open once you have applied to label.">
            <Link href="/label" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto">
              Apply to label
            </Link>
          </Gate>
        )}
        {state === "error" && <GuideFailed onRetry={() => setAttempt((n) => n + 1)} />}
      </Column>
    </div>
  );
}

function Gate({ text, children }: { text: string; children?: React.ReactNode }) {
  return (
    <div className="grid gap-4">
      <Title>Label for Prism</Title>
      <Lede>{text}</Lede>
      <div>{children}</div>
    </div>
  );
}
