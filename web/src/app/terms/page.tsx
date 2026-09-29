import type { Metadata } from "next";
import { social } from "@/lib/seo";
import { LegalPage } from "@/components/LegalPage";
import { TERMS } from "@/lib/legal";

const title = "Terms of service";
const description = "The terms for using Prism: what it is, fair use, content rights, machine-written text, paid plans.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/terms" },
  ...social(title, description, "/terms"),
};

export default function Page() {
  return <LegalPage doc={TERMS} />;
}
