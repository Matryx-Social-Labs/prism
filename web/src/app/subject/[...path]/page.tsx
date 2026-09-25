import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { SectorStrip } from "@/components/SectorStrip";
import { fetchSubject, type SubjectPage as SubjectPayload } from "@/lib/api";
import { breadcrumbLd, feedListItems, itemListLd, jsonLd } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// A node of the subject tree and the stories under it — under IT, so
// /subject/civic/crime holds the violent, the property and the ones we could
// not split. Every node is a URL and a feed or it should not exist
// (common/subjects.py); this is the half that makes that true.
export const revalidate = 120;

async function load(path: string[]): Promise<SubjectPayload | null> {
  try {
    return await fetchSubject(path.join("/"));
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ path: string[] }> }): Promise<Metadata> {
  const { path } = await params;
  const page = await load(path);
  if (!page) return { title: "Not found", robots: { index: false, follow: true } };
  const { node, ancestors, story_count } = page;
  const trail = [...ancestors.map((a) => a.label), node.label].join(" · ");
  return {
    title: `${node.label} — today's record`,
    description: `${story_count} ${story_count === 1 ? "story" : "stories"} in ${trail}, from monitored Indian and international outlets, one record per story: who reported it, what changed, who said what.`,
    alternates: { canonical: `/subject/${node.path.split(".").join("/")}` },
    // A node nobody has reached yet is not a page worth indexing. It stays
    // readable, and comes back when the corpus fills it.
    robots: story_count > 0 ? undefined : { index: false, follow: true },
  };
}

export default async function SubjectPageRoute({ params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const page = await load(path);
  if (!page) notFound();
  const { node, ancestors, children, story_count, stories } = page;
  const href = (p: string) => `/subject/${p.split(".").join("/")}`;
  const url = `${SITE_URL}${href(node.path)}`;

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(
            breadcrumbLd([
              { name: "Prism", url: `${SITE_URL}/` },
              ...ancestors.map((a) => ({ name: a.label, url: `${SITE_URL}${href(a.path)}` })),
              { name: node.label, url },
            ]),
          ),
        }}
      />
      {stories.length > 0 && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd(`${node.label} — today's record`, url, feedListItems(stories))) }}
        />
      )}
      <SectorStrip active={node.path.split(".")[0]} />
      <main className="mx-auto w-full max-w-[860px] px-4 pb-20 pt-4">
        <header className="border-t pt-3" style={{ borderColor: "var(--rule)" }}>
          {ancestors.length > 0 && (
            <nav aria-label="Breadcrumb" className="p-eyebrow">
              {ancestors.map((a) => (
                <Link key={a.path} href={href(a.path)} className="underline-offset-4 hover:underline">
                  {a.label}
                  <span aria-hidden> / </span>
                </Link>
              ))}
            </nav>
          )}
          <h1 className="font-display mt-1 text-[34px] leading-[1.08]">{node.label}</h1>
          <p className="font-mono mt-1 text-[11px]" style={{ color: "var(--ink-3)" }}>
            {story_count} {story_count === 1 ? "story" : "stories"}
          </p>
          {children.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {children.map((c) => (
                <Link key={c.path} href={href(c.path)} className="chip h-[30px] px-2.5 text-[13px]">{c.label}</Link>
              ))}
            </div>
          )}
        </header>
        {stories.length === 0 ? (
          <p className="mt-6 text-[15px]" style={{ color: "var(--ink-2)" }}>No stories here yet.</p>
        ) : (
          <ol className="p-print mt-4 grid gap-3">
            {stories.map((item, i) => (
              <ChartRow key={item.id} item={item} lead={i === 0} />
            ))}
          </ol>
        )}
      </main>
    </>
  );
}
