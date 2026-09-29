import { cardImage, trendingCard } from "@/lib/cards";

// A trending group's card (share cards v3; lib/cards): its status, subject and
// span, its headline, a verified arc's route, the counted bar.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A developing story's share card on Prism: its name, whether its grouping is verified, how many days it spans, and its coverage bar with how many of the outlets Prism monitors reported it.";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  return cardImage(trendingCard((await params).slug, "og"), "og");
}
