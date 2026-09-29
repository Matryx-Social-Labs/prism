import type { Metadata } from "next";
import Link from "next/link";
import { PageTitle } from "@/components/reading/parts";
import { BackBar } from "@/components/ui";
import { CONTACT_EMAIL } from "@/lib/legal";
import { social } from "@/lib/seo";

// Razorpay asks every merchant for a delivery policy (docs/COMPLIANCE-INDIA.md N9).
// Prism sells digital access only, so the true policy is short.
const title = "Delivery";
const description = "Prism is read online. Digital access starts the moment a payment is confirmed; nothing is shipped.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/delivery" },
  ...social(title, description, "/delivery"),
};

export default function DeliveryPage() {
  const para = { font: "var(--t-body)", color: "var(--ink-2)" } as const;
  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[720px] grid-cols-[minmax(0,1fr)] gap-4 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <PageTitle>Delivery</PageTitle>
        <p className="max-w-[60ch] text-pretty" style={para}>
          Everything Prism sells is digital. Access starts the moment your payment is confirmed: the plan opens on your account at once, with no
          waiting period.
        </p>
        <p className="max-w-[60ch] text-pretty" style={para}>
          Nothing is shipped. There is no physical product and no delivery charge.
        </p>
        <p className="max-w-[60ch] text-pretty" style={para}>
          You read on readprism.news, in a browser, wherever you sign in with the email on your account.
        </p>
        <p className="max-w-[60ch] text-pretty" style={para}>
          If access has not started after a confirmed payment, write to{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="p-link">{CONTACT_EMAIL}</a> with the payment reference from your receipt.
        </p>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          Cancelling and refunds: <Link href="/refunds" className="p-link">Refund policy</Link>. Everything else:{" "}
          <Link href="/terms" className="p-link">Terms of service</Link>.
        </p>
      </div>
    </>
  );
}
