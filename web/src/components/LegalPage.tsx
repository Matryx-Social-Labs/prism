import Link from "next/link";
import { LEGAL_DOCS, LEGAL_UPDATED, type Block, type LegalDoc } from "@/lib/legal";

// A legal document in the record's voice: title and section heads in
// Newsreader, the text in Hind at the 640 reading measure, the date in mono.
// Hairlines between sections, no cards (DESIGN.md § Components). Server-only.
export function LegalPage({ doc }: { doc: LegalDoc }) {
  const others = LEGAL_DOCS.filter((d) => d.slug !== doc.slug);
  return (
    <article className="mx-auto w-full max-w-[var(--reading)] px-5 pb-20 pt-10 sm:px-8 lg:pt-14">
      <header>
        <h1 className="font-record text-[34px] font-medium leading-[1.1] tracking-[-0.015em] text-balance sm:text-[40px]">{doc.title}</h1>
        <p className="mt-2 font-mono text-[12px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
          Last changed <time dateTime={LEGAL_UPDATED}>{LEGAL_UPDATED}</time>
        </p>
        <p className="mt-5 text-[16px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>{doc.lede}</p>
      </header>

      {doc.sections.map((s) => (
        <section key={s.heading} className="mt-8 border-t pt-5" style={{ borderColor: "var(--line)" }}>
          <h2 className="font-record text-[24px] font-medium leading-[1.2] tracking-[-0.01em]">{s.heading}</h2>
          {s.blocks.map((b, i) => <BlockView key={i} block={b} />)}
        </section>
      ))}

      <nav aria-label="Other policies" className="mt-12 flex flex-wrap gap-x-5 gap-y-2 border-t pt-5 text-[14px] font-medium" style={{ borderColor: "var(--line)" }}>
        {others.map((d) => (
          <Link key={d.slug} href={`/${d.slug}`} className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>
            {d.title} →
          </Link>
        ))}
      </nav>
    </article>
  );
}

function BlockView({ block }: { block: Block }) {
  if (typeof block === "string") return <p className="mt-3 text-[16px] leading-[1.6]">{block}</p>;
  return (
    <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[16px] leading-[1.6]">
      {block.map((li) => <li key={li}>{li}</li>)}
    </ul>
  );
}
