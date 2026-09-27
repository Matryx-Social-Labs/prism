// A model's confidence is its own number, not a measurement; printed as "0.6"
// or "60%" it reads as precision Prism does not have (DESIGN.md: no invented
// numbers). A reader gets it in words.
const LOW_BELOW = 0.5;
const HIGH_FROM = 0.75;

/** 0.4 → "low confidence", 0.6 → "moderate confidence", 0.8 → "high confidence". */
export function confidenceWords(confidence: number): string {
  if (confidence < LOW_BELOW) return "low confidence";
  if (confidence < HIGH_FROM) return "moderate confidence";
  return "high confidence";
}
