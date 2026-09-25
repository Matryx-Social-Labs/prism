import { SystemPage } from "@/components/ui";

// Any address with no page, and every notFound() a route calls (a story, an
// entity or a subject that does not exist): the record's own 404, not Next's.
export default function NotFound() {
  return <SystemPage kind={404} />;
}
