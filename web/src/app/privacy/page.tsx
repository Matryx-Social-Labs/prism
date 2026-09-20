import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { PRIVACY } from "@/lib/legal";

export const metadata: Metadata = { title: "Privacy policy", description: "What Prism collects, why, who processes it, how long it is kept, and your rights under the DPDP Act.", alternates: { canonical: "/privacy" } };

export default function Page() {
  return <LegalPage doc={PRIVACY} />;
}
