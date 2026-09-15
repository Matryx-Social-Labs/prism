"use client";

import { use } from "react";
import { FrontPage } from "@/components/FrontPage";

// The chart filtered to one of the reader's six subjects, its code active in
// the strip. Legacy pipeline slugs (/sector/finance) resolve to their group;
// an unknown slug shows the whole chart rather than a dead end.
export default function SectorPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  return <FrontPage sector={slug} />;
}
