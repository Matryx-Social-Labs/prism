import { notFound } from "next/navigation";
import { fetchEvent } from "@/lib/api";
import { StoryView } from "@/components/StoryView";

export const dynamic = "force-dynamic";

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let event;
  try {
    event = await fetchEvent(id);
  } catch {
    notFound();
  }
  if (!event) notFound();

  return <StoryView event={event} />;
}
