import { cardImage, quoteCard } from "@/lib/cards";

// The quote card (PLAN-LAUNCH §6, share cards v3; lib/cards): the sentence as
// the article printed it, who said it, where and when, and what the check
// proved. The most shared thing on WhatsApp is a sentence.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A quote's share card on Prism: the words as the article printed them, who said them, the outlet, time and language, and how the words were checked against the article.";

export default async function Image({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id, n } = await params;
  return cardImage(quoteCard(id, n, "og"), "og");
}
