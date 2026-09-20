/**
 * How long the lens flip sweeps a block of this height (ms). A constant pace
 * of ~0.9px per ms, held between 500ms (a short locked box) and 1100ms (a long
 * brief with its watch points), so the scan line and the re-ink read the same
 * on every record instead of racing through the tall ones.
 */
export function flipDuration(heightPx: number): number {
  return Math.round(Math.min(1100, Math.max(500, heightPx / 0.9)));
}
