import { cardImage, storyCard } from "@/lib/cards";

// Social card for a shared /story/<id> link (share cards v3; lib/cards): the
// record's status as its page prints it, the mono meta line, the headline at
// poster scale, the coverage bar in the outlets' slot colours with its counts.
// No publisher photograph, ever.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A Prism record's share card: its headline, its status, when it was last updated, and its coverage bar with how many of the outlets Prism monitors reported it.";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  return cardImage(storyCard((await params).id, "og"), "og");
}
