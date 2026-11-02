import Link from "next/link";
import { GRIEVANCE_KINDS, grievanceHref } from "@/lib/grievance";

/**
 * The structured ways to tell Prism a record is wrong. Community is structured,
 * never comments: each kind opens the complaint form on /grievance with the
 * kind and the record's address already filled in, so a report arrives saying
 * what and where, is acknowledged at once and is counted in the monthly report
 * (IT Rules Part III; api/routes/grievances.py).
 */
export const PROBLEMS = GRIEVANCE_KINDS.slice(0, 4);

export function ReportProblem({ path }: { path?: string }) {
  return (
    <ul className="flex flex-col" aria-label="Report a problem">
      {PROBLEMS.map((kind) => (
        <li key={kind} className="border-t first:border-t-0" style={{ borderColor: "var(--line)" }}>
          {/* Never prefetched or followed: each story's four addresses are new to the
              cache and /grievance renders on the server, so crawlers and prefetches cost
              four renders per story view — 43% of all Vercel requests (2026-11-02). */}
          <Link href={grievanceHref(kind, path)} prefetch={false} rel="nofollow" className="flex min-h-[44px] items-center text-[14.5px] underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
            {kind}
          </Link>
        </li>
      ))}
    </ul>
  );
}
