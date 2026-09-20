# Search and answer-engine visibility (SEO / GEO)

What is in place as of 2026-09-21, why, and what only the founder's accounts can
do. The principle: **the record must be in the HTML.** Google renders JavaScript
late and on a budget; the answer engines' crawlers (GPTBot, ClaudeBot,
PerplexityBot, Google-Extended) do not render it at all. Before this work the
day's record, the sector pages and Stories shipped a skeleton and nothing else.

## In the code

| Surface | What a crawler now gets | Where |
|---|---|---|
| `/feed`, `/sector/<slug>` | The ALL list (60 rows) server-rendered, revalidated every 60 s; one `h1`; a canonical; an `ItemList` JSON-LD of the rows. The client re-fetches only when the reader's own slice differs (state, language, FOR YOU). Unknown sector slugs 404 (they used to render the whole chart under the root title). | `app/feed/page.tsx`, `app/sector/[slug]/page.tsx`, `components/FrontPage.tsx` |
| `/trending` | The national list of stories server-rendered (120 s), `h1`, canonical, `ItemList`. | `app/trending/page.tsx`, `components/StoriesPage.tsx` |
| `/story/<id>` | `NewsArticle` with `mainEntityOfPage`, dates, `isBasedOn` (the reports it is written from, with their publishers and languages), `about` (named entities), `keywords`, `isAccessibleForFree`, the publisher by `@id`. Never an image (the photograph is the outlet's). | `lib/seo.ts` `newsArticleLd` |
| `/trending/<slug>` | `NewsArticle` for the arc with `hasPart` = its developments, dated from the first and last. | `lib/seo.ts` `storyLd` |
| Every page | `NewsMediaOrganization` (brand Prism, `legalName` the LLP, logo, publishing principles → `/about`) + `WebSite` with a `SearchAction`; `robots` meta with `max-snippet:-1`, `max-image-preview:large`; theme colours; canonicals on `/about`, `/plus`, `/pulse`, the policies. `/search` is `noindex, follow`. `/plus` renders per request (statically it bailed out to an empty Suspense fallback). | `app/layout.tsx`, each page's metadata |
| `/sitemap.xml` | Static pages, the six subjects, up to 100 stories, up to 500 records with `lastmod`. | `app/sitemap.ts` |
| `/news-sitemap.xml` | Google News sitemap: records of the last 48 hours, publication "Prism", language `en`. | `app/news-sitemap.xml/route.ts` |
| `/robots.txt` | Everything public allowed for every agent (AI crawlers included — being cited is the point); account, auth, `/you`, `/search`, `/label/`, `/plus/welcome` disallowed; both sitemaps listed. | `app/robots.ts` |
| `/llms.txt` | What Prism is, how to cite a record, the live URLs — the emerging convention answer engines read first. | `public/llms.txt` |
| `/manifest.webmanifest` | Installable: name, icons (brand exports), `start_url` `/feed`, theme. | `app/manifest.ts` |
| IndexNow | Every hour the worker posts the records and stories that changed to `api.indexnow.org` (Bing → Copilot and ChatGPT search; Yandex; Naver). The key is public by design and served at `/<key>.txt`. Google ignores IndexNow; the sitemaps carry it there. | `common/indexnow.py`, `worker/__main__.py` job `indexnow` |

Share cards (OG images) were already the record's own (`lib/ogCard.tsx`);
nothing here changes them.

## Owner's checklist (needs your accounts)

1. **Google Search Console** — add `https://www.readprism.news` (Domain
   property via DNS TXT is best). Submit `sitemap.xml` and `news-sitemap.xml`.
   Once verified, if you want the meta-tag route instead, add
   `verification.google` to `metadata` in `app/layout.tsx`.
2. **Google Publisher Center** — register Prism as a publication so the news
   sitemap is read as news. Requirements: an About page (`/about`), contact
   details, the legal entity, and consistent bylines ("Headline by Prism").
3. **Bing Webmaster Tools** — import from Search Console (one click). IndexNow
   submissions show up under "IndexNow" there; the first acceptance can take a
   day while the key is verified.
4. **Plausible** — set `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` (Vercel + ci.yml pin) and
   add the sentence to `/privacy`; search-console data does not need it.
5. **The mailbox** `hello@readprism.news` is named in `llms.txt`, the policies
   and the refund flow — it needs an inbound route (Resend inbound, or a
   forward at the registrar).
6. **Google-Extended / CCBot** — the file allows them today (training crawlers).
   If you want Prism read for answers but not trained on, add a `Disallow: /`
   rule for `Google-Extended`, `CCBot`, `Applebot-Extended` in `app/robots.ts`
   (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `OAI-SearchBot` stay allowed — those
   are the citing crawlers). It is a policy call, not a technical one.

## How to check it is working

```
curl -sA "Mozilla/5.0 (compatible; GPTBot/1.0)" https://www.readprism.news/feed | grep -c row-card   # 60
curl -s https://www.readprism.news/news-sitemap.xml | grep -c "<news:news>"
curl -s https://www.readprism.news/llms.txt | head -3
```

Google's Rich Results Test (search.google.com/test/rich-results) on a `/story/<id>`
URL should show one NewsArticle with no errors; the Schema validator
(validator.schema.org) will show the `isBasedOn` list. Search Console →
Sitemaps shows both files discovered; Bing Webmaster → IndexNow shows the hourly
batches.
