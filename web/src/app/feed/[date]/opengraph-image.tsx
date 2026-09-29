import { cardImage, dayCard } from "@/lib/cards";

// One IST day's card (lib/cards): the date, its stories from two or more
// outlets, those from one, its languages; or that Prism was not reading.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A Prism share card for one day's record: the date, how many stories two or more monitored outlets reported that day, how many one outlet did, and in how many languages.";

export default async function Image({ params }: { params: Promise<{ date: string }> }) {
  return cardImage(dayCard((await params).date, "og"), "og");
}
