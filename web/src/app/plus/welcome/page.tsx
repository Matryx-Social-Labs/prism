import type { Metadata } from "next";
import { Suspense } from "react";
import { PlusWelcome } from "@/components/PlusWelcome";

export const metadata: Metadata = { title: "You're on Plus", robots: { index: false } };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <PlusWelcome />
    </Suspense>
  );
}
