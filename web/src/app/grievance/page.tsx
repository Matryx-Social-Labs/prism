import type { Metadata } from "next";
import Link from "next/link";
import { GrievanceForm } from "@/components/GrievanceForm";
import { PageTitle } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { Alert, BackBar } from "@/components/ui";
import { fetchGrievanceReport, recordPath, type GrievanceMonth } from "@/lib/grievance";
import { GRIEVANCE_ADDRESS, GRIEVANCE_OFFICER, LEGAL_ENTITY } from "@/lib/legal";
import { social } from "@/lib/seo";

// The IT Rules' grievance page (Part III, R10–R11, R18(3), R19; docs/COMPLIANCE-INDIA.md
// N1–N3): who the officer is and how to reach them, the two clocks, the form,
// and every month's count since the mechanism opened, zeros printed.
const title = "Grievances";
const description = `Complain about anything on Prism. Acknowledged within 24 hours with a copy of your complaint, and decided within 15 days by ${GRIEVANCE_OFFICER.name}, Prism's Grievance Officer.`;
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/grievance" },
  ...social(title, description, "/grievance"),
};

type Query = { kind?: string | string[]; record?: string | string[] };
const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const monthName = (ym: string) => new Date(`${ym}-15T00:00:00Z`).toLocaleDateString("en-IN", { month: "long", year: "numeric", timeZone: "UTC" });

export default async function GrievancePage({ searchParams }: { searchParams: Promise<Query> }) {
  const [q, report] = await Promise.all([searchParams, fetchGrievanceReport()]);
  const officer: [string, React.ReactNode][] = [
    ["Name", GRIEVANCE_OFFICER.name],
    ["Designation", GRIEVANCE_OFFICER.designation],
    ["Organisation", LEGAL_ENTITY],
    ["Email", <a key="e" href={`mailto:${GRIEVANCE_OFFICER.email}`} className="p-link">{GRIEVANCE_OFFICER.email}</a>],
    ["Address", GRIEVANCE_ADDRESS],
  ];
  return (
    <>
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[720px] grid-cols-[minmax(0,1fr)] gap-7 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-2">
          <PageTitle>Grievances</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            Anything on Prism you think is wrong can be raised here: a record, a quote, how your data is handled, a payment. Every complaint is
            acknowledged within 24 hours with a copy of it as recorded, and decided within 15 days.
          </p>
        </header>

        <section aria-labelledby="officer" className="grid gap-2">
          <SectionHead id="officer" title="Grievance Officer" />
          <dl className="m-0 grid grid-cols-[auto_minmax(0,1fr)] gap-x-5 gap-y-2" style={{ font: "var(--t-body-s)" }}>
            {officer.map(([k, v]) => (
              <div key={k} className="contents">
                <dt style={{ color: "var(--ink-3)" }}>{k}</dt>
                <dd className="m-0 min-w-0" style={{ overflowWrap: "anywhere" }}>{v}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section aria-labelledby="how" className="grid gap-3">
          <SectionHead id="how" title="How it works" />
          <ol className="grid gap-2.5" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            <li><b style={{ color: "var(--ink)" }}>Acknowledged within 24 hours.</b> A complaint made here is acknowledged by email the moment it is sent, with a copy of it as we recorded it and a reference to quote.</li>
            <li><b style={{ color: "var(--ink)" }}>Decided within 15 days.</b> The Grievance Officer writes to you with the decision and what was done about it.</li>
            <li><b style={{ color: "var(--ink)" }}>Counted in public.</b> Every month&rsquo;s complaints are counted below: received, resolved, rejected and still open.</li>
          </ol>
          <p className="max-w-[60ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
            What to include: the page it is about, what is wrong, and what it should say. For a quote, the words; for a payment, the payment reference
            from your receipt; for your data, the email on your account. You can also write to{" "}
            <a href={`mailto:${GRIEVANCE_OFFICER.email}`} className="p-link">{GRIEVANCE_OFFICER.email}</a>.
          </p>
        </section>

        <section id="complain" aria-labelledby="complain-title" className="grid scroll-mt-24 gap-3">
          <SectionHead id="complain-title" title="Make a complaint" />
          <GrievanceForm initialKind={first(q.kind)} initialRecord={recordPath(first(q.record))} />
        </section>

        <section aria-labelledby="report" className="grid gap-2">
          <SectionHead id="report" title="Complaints by month" sub={report ? `Counted by the month received · IST · since ${monthName(report.since.slice(0, 7))}` : undefined} />
          {report ? <ReportTable months={report.months} /> : <Alert tone="error" title="The monthly count cannot be reached right now.">Try again in a minute.</Alert>}
        </section>

        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          Corrections Prism has made to its records are listed on <Link href="/corrections" className="p-link">Corrections</Link>. How your data is
          handled: <Link href="/privacy" className="p-link">Privacy policy</Link>.
        </p>
      </div>
    </>
  );
}

function ReportTable({ months }: { months: GrievanceMonth[] }) {
  return (
    <div className="overflow-x-auto overflow-y-hidden overscroll-x-contain">
      <table className="p-table">
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col" className="num">Received</th>
            <th scope="col" className="num">Resolved</th>
            <th scope="col" className="num">Rejected</th>
            <th scope="col" className="num">Open</th>
            <th scope="col" className="num">Median days to decide</th>
          </tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month}>
              <th scope="row" style={{ font: "var(--t-body-s)", textTransform: "none", letterSpacing: 0, color: "var(--ink)", padding: 10 }}>{monthName(m.month)}</th>
              <td className="num">{m.received}</td>
              <td className="num">{m.resolved}</td>
              <td className="num">{m.rejected}</td>
              <td className="num">{m.open}</td>
              <td className="num">{m.median_days ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>A dash: nothing received that month has been decided yet.</p>
    </div>
  );
}
