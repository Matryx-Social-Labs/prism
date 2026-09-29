import { notFound } from "next/navigation";

import { cardForPath, cardImage } from "@/lib/cards";
import type { CardFormat } from "@/lib/ogCard";

// A page's share card in Instagram's shapes, for the founders' Marketing page:
// /card/portrait/<path> (a 4:5 post) and /card/story/<path> (a 9:16 Story).
// The same card as the link preview (lib/cards), laid out for the shape. Kept
// out of search and off crawlers (robots.ts); cached ten minutes, because the
// counts on it move and a founder downloads it again.
const SHAPES: ReadonlySet<CardFormat> = new Set(["portrait", "story"]);

export async function GET(_req: Request, { params }: { params: Promise<{ format: string; path: string[] }> }) {
  const { format, path } = await params;
  if (!SHAPES.has(format as CardFormat)) notFound();
  const shape = format as CardFormat;
  return cardImage(cardForPath(path.map(decodeURIComponent), shape), shape, {
    "cache-control": "public, max-age=600, s-maxage=600",
    "x-robots-tag": "noindex",
  });
}
