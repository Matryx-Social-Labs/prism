import type { Metadata } from "next";
import { social } from "@/lib/seo";
import { LegalPage } from "@/components/LegalPage";
import { PRIVACY } from "@/lib/legal";

const title = "Privacy policy";
const description = "What Prism collects, why, who processes it, how long it is kept, and your rights under the DPDP Act.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/privacy" },
  ...social(title, description, "/privacy"),
};

export default function Page() {
  return <LegalPage doc={PRIVACY} />;
}
