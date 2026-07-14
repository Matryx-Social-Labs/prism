"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchLenses, type LensInfo } from "@/lib/api";
import { loadProfile, saveProfile } from "@/lib/profile";

const FALLBACK_LENSES: LensInfo[] = [
  { slug: "cyber_grc", name: "Cybersecurity / GRC", tagline: "CVEs, incidents, and what they mean for your controls" },
  { slug: "finance_trader", name: "Finance / Trader", tagline: "Market-moving news with tickers, catalysts, and price-impact reads" },
  { slug: "general", name: "General reader", tagline: "Every story with both sides, consequences, and answers" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [lenses, setLenses] = useState<LensInfo[]>(FALLBACK_LENSES);
  const [selected, setSelected] = useState<string>("cyber_grc");

  useEffect(() => {
    const existing = loadProfile();
    if (existing) setSelected(existing.lens);
    fetchLenses().then((remote) => {
      if (remote.length > 0) setLenses(remote);
    });
  }, []);

  function submit() {
    saveProfile({ lens: selected });
    router.push("/feed");
  }

  return (
    <div className="mx-auto max-w-xl py-10">
      <h1 className="text-2xl font-bold">What&apos;s your role?</h1>
      <p className="mt-2 text-sm text-stone-500">
        Your role picks a lens: which fields Prism extracts for you, how your feed is
        ranked, and what the per-story agent suggests asking. You can change it anytime.
      </p>

      <div className="mt-8 space-y-3">
        {lenses.map((lens) => (
          <button
            key={lens.slug}
            onClick={() => setSelected(lens.slug)}
            className={`block w-full rounded-xl border p-4 text-left transition ${
              selected === lens.slug
                ? "border-stone-900 ring-1 ring-stone-900 dark:border-stone-100 dark:ring-stone-100"
                : "border-stone-200 hover:border-stone-400 dark:border-stone-800 dark:hover:border-stone-600"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold">{lens.name}</span>
              {selected === lens.slug && <span aria-hidden>●</span>}
            </div>
            <p className="mt-1 text-sm text-stone-500">{lens.tagline}</p>
          </button>
        ))}
      </div>

      <button
        onClick={submit}
        className="mt-8 w-full rounded-lg bg-stone-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-stone-700 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
      >
        Build my feed →
      </button>
    </div>
  );
}
