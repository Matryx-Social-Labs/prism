"use client";

import { useEffect, useState } from "react";

import { fetchRegions } from "@/lib/api";

// Resolve an ISO 3166-2 state code to its display name.
//
// Trending carried a hand-written map of seven states, so a reader in Bihar,
// Punjab, Odisha or anywhere else outside that list saw the raw "IN-BR" in the
// scope chip — while the Feed, one tab away, resolved the same code properly
// from /api/v1/regions. The API knows all 36; nobody needs to maintain a list.
//
// Cached at module scope: the region list is a static taxonomy, and both
// surfaces mount it repeatedly as the reader moves between tabs.
let cache: Promise<Map<string, string>> | null = null;

function regionNames(): Promise<Map<string, string>> {
  cache ??= fetchRegions()
    .then((rs) => new Map(rs.map((r) => [r.code, r.name])))
    .catch(() => {
      cache = null; // a failed fetch shouldn't poison every later mount
      return new Map<string, string>();
    });
  return cache;
}

/**
 * The state's name, or the code itself until the list arrives (and if it never
 * does). Returns null for a reader with no state, so callers can fall back to
 * their own "Your state" copy.
 */
export function useStateName(code: string | null): string | null {
  const [name, setName] = useState<string | null>(code);

  useEffect(() => {
    if (!code) {
      setName(null);
      return;
    }
    let cancelled = false;
    setName(code); // show something immediately rather than an empty chip
    regionNames().then((m) => {
      if (!cancelled) setName(m.get(code) ?? code);
    });
    return () => {
      cancelled = true;
    };
  }, [code]);

  return name;
}
