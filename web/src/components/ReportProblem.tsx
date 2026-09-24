import { CONTACT_EMAIL } from "@/lib/legal";
import { SITE_URL } from "@/lib/site";

/**
 * The structured ways to tell Prism a record is wrong. Community is structured,
 * never comments: each kind opens the reader's own mail with the record's
 * address and the kind of problem already filled in, so a report arrives
 * saying what and where. No form and nothing stored until someone writes.
 * ponytail: mailto until a grievance/corrections queue exists (docs/COMPLIANCE-INDIA.md
 * decides its shape); then these become a form posting to it.
 */
export const PROBLEMS = [
  "A fact is wrong",
  "A quote is not in the article",
  "An outlet says something different",
  "An outlet that covered this is missing",
] as const;

export function problemHref(kind: string, path?: string): string {
  const subject = path ? `${kind} · ${path}` : kind;
  const body = `${path ? `Record: ${SITE_URL}${path}\n\n` : ""}What is wrong, and where you saw it:\n`;
  return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function ReportProblem({ path }: { path?: string }) {
  return (
    <ul className="flex flex-col" aria-label="Report a problem">
      {PROBLEMS.map((kind) => (
        <li key={kind} className="border-t first:border-t-0" style={{ borderColor: "var(--line)" }}>
          <a href={problemHref(kind, path)} className="flex min-h-[44px] items-center text-[14.5px] underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>
            {kind}
          </a>
        </li>
      ))}
    </ul>
  );
}
