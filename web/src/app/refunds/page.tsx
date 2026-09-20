import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { REFUNDS } from "@/lib/legal";

export const metadata: Metadata = { title: "Refund policy", description: "Monthly plans are not refunded; annual plans are refunded in full within 7 days of a charge." };

export default function Page() {
  return <LegalPage doc={REFUNDS} />;
}
