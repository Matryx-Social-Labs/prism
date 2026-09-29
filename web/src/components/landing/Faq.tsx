import { ChevronDown } from "@/components/icons";
import { Reveal } from "@/components/Reveal";
import type { Faq as FaqItem } from "@/lib/faq";

/**
 * Questions and answers as native <details> rows (the /plus FAQ pattern): no
 * script, every answer in the HTML a crawler reads, and the same text the
 * page's FAQPage JSON-LD carries (lib/seo faqLd).
 */
export function Faq({ id, title, items }: { id: string; title: string; items: FaqItem[] }) {
  return (
    <section id={id} className="sc-shell scroll-mt-20 pt-16" aria-labelledby={`${id}-title`}>
      <Reveal><h2 id={`${id}-title`} style={{ font: "var(--t-display-m)" }}>{title}</h2></Reveal>
      <div className="mt-4 max-w-[760px]">
        {items.map((f) => (
          <details key={f.q} className="group py-1" style={{ borderTop: "1px solid var(--line)" }}>
            <summary className="flex min-h-[52px] cursor-pointer list-none items-center gap-3 [&::-webkit-details-marker]:hidden" style={{ font: "600 15.5px/1.35 var(--font-read)" }}>
              <span className="min-w-0 flex-1">{f.q}</span>
              <span className="transition-transform group-open:rotate-180" style={{ color: "var(--ink-3)" }} aria-hidden><ChevronDown size={14} /></span>
            </summary>
            <p className="max-w-[62ch] pb-3.5" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
