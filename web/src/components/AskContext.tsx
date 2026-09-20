"use client";

import { createContext, useContext } from "react";

// How the rest of the record opens Ask: the persistent bar, a selection, a
// quote card, an entity card. One panel; these only decide what it opens
// with. `via` is the analytics label, never the question text.
export type AskVia = "bar" | "foot" | "thumb" | "selection" | "quote" | "entity" | "chip";
export interface AskOpen {
  prefill?: string;
  /** Send `prefill` at once instead of leaving it in the input to edit. */
  submit?: boolean;
  via: AskVia;
}

export const AskContext = createContext<((o: AskOpen) => void) | null>(null);

/** The opener, or null where no Ask panel is mounted (the landing, the explainer). */
export function useAsk(): ((o: AskOpen) => void) | null {
  return useContext(AskContext);
}
