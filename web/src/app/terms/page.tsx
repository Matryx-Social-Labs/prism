import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { TERMS } from "@/lib/legal";

export const metadata: Metadata = { title: "Terms of service", description: "The terms for using Prism: what it is, fair use, content rights, machine-written text, paid plans." };

export default function Page() {
  return <LegalPage doc={TERMS} />;
}
