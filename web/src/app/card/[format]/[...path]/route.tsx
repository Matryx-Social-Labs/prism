import { notFound } from "next/navigation";

import { cardForPath, cardImage } from "@/lib/cards";
import type { CardFormat } from "@/lib/ogCard";

// A page's share card in Instagram's shapes, for the founders' Marketing page:
// /card/portrait/<path> (a 4:5 post) and /card/story/<path> (a 9:16 Story).
// The same card as the link preview (lib/cards), laid out for the shape. Kept
// out of search and off crawlers (robots.ts); cached ten minutes, because the
// counts on it move and a founder downloads it again. Anything that is not a
// real page's card is a 404 before a pixel is drawn: every render costs CPU,
// and the route is public (the brand card is /card/<format>/site).
const SHAPES: ReadonlySet<CardFormat> = new Set(["portrait", "story"]);

export async function GET(_req: Request, { params }: { params: Promise<{ format: string; path: string[] }> }) {
  const { format, path } = await params;
  if (!SHAPES.has(format as CardFormat)) notFound();
  const shape = format as CardFormat;
  let segments: string[];
  try {
    segments = path.map(decodeURIComponent);
  } catch {
    notFound(); // a malformed escape, such as %E0%A4%A
  }
  const card = await cardForPath(segments, shape).catch(() => null);
  if (!card) notFound();
  return cardImage(Promise.resolve(card), shape, { "cache-control": "public, max-age=600, s-maxage=600", "x-robots-tag": "noindex" });
}
