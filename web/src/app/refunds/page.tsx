import type { Metadata } from "next";
import { social } from "@/lib/seo";
import { LegalPage } from "@/components/LegalPage";
import { REFUNDS } from "@/lib/legal";

const title = "Refund policy";
const description = "Monthly plans are not refunded; annual plans are refunded in full within 7 days of a charge.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/refunds" },
  ...social(title, description, "/refunds"),
};

export default function Page() {
  return <LegalPage doc={REFUNDS} />;
}
