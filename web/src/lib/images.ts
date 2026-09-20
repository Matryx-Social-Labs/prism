// Publisher photographs are shown only as credited link previews of the report
// they came from, and only while this switch is on: the right to even that much
// is not settled in India (DESIGN.md § Images). Off = no image anywhere.
export const REPORT_IMAGES = process.env.NEXT_PUBLIC_REPORT_IMAGES !== "0";

/** dHash bits apart at which two photos are the same photo (crops and re-encodes land ≤ 6). */
export const NEAR_DUPLICATE_BITS = 8;

export function hamming(a: string, b: string): number {
  let x = BigInt(`0x${a}`) ^ BigInt(`0x${b}`);
  let n = 0;
  while (x) { n += Number(x & 1n); x >>= 1n; }
  return n;
}
