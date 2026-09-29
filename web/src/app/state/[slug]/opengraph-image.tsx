import { cardImage, stateCard } from "@/lib/cards";

// A state's card (lib/cards): its name, its stories from two or more outlets
// in the window, all its records, and the outlets with a desk there.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A Prism share card for a state: its name, how many stories two or more monitored outlets reported there in the last 30 days, all its records, and how many outlets have a desk there.";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  return cardImage(stateCard((await params).slug, "og"), "og");
}
