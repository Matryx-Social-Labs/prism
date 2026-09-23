"use client";

/**
 * One task kind, taught: what it asks, DO / DO NOT, and worked examples — the
 * same guide a labeller meets before a batch, readable before anyone is
 * approved or has a batch to open (labeller workspace plan, phase 2).
 *
 * The first round shipped its guidance collapsed and the two labellers came
 * back with opposite systematic biases, "because nothing made them" read it.
 * This page is where it can be read at leisure; phase 3 is what makes it count.
 */

import { notFound, useRouter } from "next/navigation";
import { use } from "react";

import { ClaimGuide, Guide, Primer } from "@/components/label/guides";
import { LEARNABLE } from "@/lib/labeller";

export default function LearnTask({ params }: { params: Promise<{ kind: string }> }) {
  const { kind } = use(params);
  const router = useRouter();
  if (!LEARNABLE.includes(kind)) notFound();
  // Story and claim primers carry their DO / DO NOT and real mistakes; their
  // invented worked examples live in the "How to decide" guide the task page
  // shows beside each task, opened here. The other two primers already hold theirs.
  const more = kind === "story_boundary" ? <Guide open /> : kind === "claim_attribution" ? <ClaimGuide open /> : null;
  return (
    <main className="mx-auto min-h-dvh w-full max-w-[720px] px-5 pb-24 pt-6 sm:px-8">
      <Primer kind={kind} onStart={() => router.push("/label")} action="Back to your workspace">
        {more}
      </Primer>
    </main>
  );
}
