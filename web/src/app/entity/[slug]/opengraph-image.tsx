import { cardImage, entityCard } from "@/lib/cards";

// A person's or organisation's card (lib/cards): what the page says they are,
// their name, and the page's own counts. No coverage bar: the page lists its
// newest records, and a bar drawn from them would undercount the outlets.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A Prism share card for a person or organisation: their name, their role as the articles put it, and how many Prism records name them and quote them.";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  return cardImage(entityCard((await params).slug, "og"), "og");
}
