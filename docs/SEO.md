# Search and answer-engine visibility (SEO / GEO)

What is in place as of 2026-09-21, why, and what only the founder's accounts can
do. The principle: **the record must be in the HTML.** Google renders JavaScript
late and on a budget; the answer engines' crawlers (OAI-SearchBot,
Claude-SearchBot, PerplexityBot) do not render it at all. Before this work the
day's record, the sector pages and Stories shipped a skeleton and nothing else.

## In the code

| Surface | What a crawler now gets | Where |
|---|---|---|
| `/feed`, `/sector/<slug>` | The ALL list (60 rows) server-rendered, revalidated every 60 s; one `h1`; a canonical; an `ItemList` JSON-LD of the rows. The client re-fetches only when the reader's own slice differs (state, language, FOR YOU). Unknown sector slugs 404 (they used to render the whole chart under the root title). | `app/feed/page.tsx`, `app/sector/[slug]/page.tsx`, `components/FrontPage.tsx` |
| `/trending` | The national list of stories server-rendered (120 s), `h1`, canonical, `ItemList`. | `app/trending/page.tsx`, `components/StoriesPage.tsx` |
| `/story/<id>` | `NewsArticle` with `mainEntityOfPage`, dates, `isBasedOn` (the reports it is written from, with their publishers and languages), `about` (named entities), `keywords`, `isAccessibleForFree`, the publisher by `@id`. Never an image (the photograph is the outlet's). | `lib/seo.ts` `newsArticleLd` |
| `/trending/<slug>` | `NewsArticle` for the arc with `hasPart` = its developments, dated from the first and last. | `lib/seo.ts` `storyLd` |
| Every page | `NewsMediaOrganization` (brand Prism, `legalName` the LLP, logo, publishing principles → `/about`) + `WebSite` with a `SearchAction`; `robots` meta with `max-snippet:-1`, `max-image-preview:large`; theme colours; canonicals on `/about`, `/plus`, `/pulse`, the policies. `/search` is `noindex, follow`. `/plus` renders per request (statically it bailed out to an empty Suspense fallback). | `app/layout.tsx`, each page's metadata |
| `/sitemap.xml` | Static pages, the six subjects, the subject-tree nodes a sector page does not already list, up to 100 stories, the freshest 100 records with `lastmod` (the feed API's page cap). Not `/pulse` (it renders in the browser; `noindex` until it renders on the server). | `app/sitemap.ts` |
| `/news-sitemap.xml` | Google News sitemap: records of the last 48 hours, publication "Prism", language `en`. | `app/news-sitemap.xml/route.ts` |
| `/robots.txt` | Everything public allowed for every agent (AI crawlers included — being cited is the point); account, auth, `/you`, `/search`, `/label/`, `/plus/welcome` disallowed; both sitemaps listed. | `app/robots.ts` |
| `/llms.txt` | What Prism is, how to cite a record, the live URLs — the emerging convention answer engines read first. | `public/llms.txt` |
| `/manifest.webmanifest` | Installable: name, icons (brand exports), `start_url` `/feed`, theme. | `app/manifest.ts` |
| IndexNow | Every hour the worker posts the records and stories that changed (only what asks to be indexed: records from two outlets, verified stories) to `api.indexnow.org` (Bing → Copilot and ChatGPT search; Yandex; Naver). The key is public by design and served at `/<key>.txt`. Google ignores IndexNow; the sitemaps carry it there. | `common/indexnow.py`, `worker/__main__.py` job `indexnow` |

Share cards (OG images) were already the record's own (`lib/ogCard.tsx`);
nothing here changes them.

## Owner's checklist (needs your accounts)

1. **Google Search Console** — add `https://www.readprism.news` (Domain
   property via DNS TXT is best). Submit `sitemap.xml` and `news-sitemap.xml`.
   Once verified, if you want the meta-tag route instead, add
   `verification.google` to `metadata` in `app/layout.tsx`.
2. **Google Publisher Center — SKIP IT (checked 2026-09-22).** The manual
   Google News setup it used to hold is gone: publication pages are
   auto-generated (March 2025) and there is no news-sitemap field, no
   categories and no publish step to find. Google's own documentation now
   says publishers "are automatically considered for Top stories or the News
   tab of Search. They just need to produce high-quality content and comply
   with Google News content policies." What remains in Publisher Center is
   Showcase, a paid licensing programme, and editing an auto-generated page
   if one appears. Nothing there gates ranking. Google News inclusion is
   earned by the content plus the signals already shipped (NewsArticle with
   an image, dates, canonical, `news-sitemap.xml`, which Google reads whether
   or not it is registered anywhere) — and watched in Search Console under
   Performance → Search type → News.
3. **Bing Webmaster Tools** — import from Search Console (one click). IndexNow
   submissions show up under "IndexNow" there; the first acceptance can take a
   day while the key is verified.
4. ~~**Plausible**~~ — no account; deliberately skipped 2026-09-22. It measures ranking rather than affecting it; Search Console's Performance report is the baseline until there is traffic worth a second tool.
5. ~~**The mailbox** `hello@readprism.news`~~ — DONE 2026-09-22: a forwarding alias at the registrar. It is named in `llms.txt`, the policies, the refund flow and the organisation schema, and now reaches a person.
6. ~~**Google-Extended / CCBot**~~ — DECIDED and SHIPPED in 0.0.86.0: the
   training-only crawlers (`Google-Extended`, `CCBot`, `Applebot-Extended`,
   `Bytespider`, `meta-externalagent`, and since 2026-09-29 `GPTBot` and
   `ClaudeBot`, which their vendors document as training crawlers) are
   disallowed; the citing crawlers (`OAI-SearchBot`, `ChatGPT-User`,
   `Claude-SearchBot`, `Claude-User`, `PerplexityBot`) stay allowed. The
   trade-off is written beside the rule in `app/robots.ts`.

## Rank sooner — the order that matters (2026-09-22)

Status on 2026-09-22: none of the owner-side items below is done. The code side
(this file, plus 0.0.86.0: the record's own image in the schema, the records
sitemap, `<time>` dates, breadcrumbs, ISR, the robots split) ships regardless;
these are what turn it into traffic, and each unlocks the next.

| # | Do | Unlocks | Time |
|---|---|---|---|
| 1 | **Google Search Console**: Domain property for `readprism.news` (DNS TXT at the registrar), then submit `sitemap.xml`, `news-sitemap.xml`, `records-sitemap.xml` | Every later diagnostic (indexed? Discover? Publisher Center check?) reads from here | 15 min + DNS |
| 2 | **Bing Webmaster Tools** → "Import from Search Console" | Bing's index (Copilot and ChatGPT search read it) and the IndexNow dashboard that shows the worker's hourly pings landing | 5 min |
| 3 | ~~Google Publisher Center~~ — **not a step any more** (checked 2026-09-22): the manual news setup is gone and inclusion is automatic. Instead, make `/about#status` say plainly how a record is written and corrected — the bylines read "Headline by Prism", and editorial accountability is what a policy review looks for | Google News / Top Stories eligibility, which is now earned by content + the shipped signals, not by registration | 20 min on /about |
| 4 | ~~`hello@readprism.news` inbound~~ — **DONE** 2026-09-22 (registrar forwarding alias) | Corrections and takedowns reach a person | — |
| 5 | ~~Plausible~~ — **skipped** 2026-09-22, no account. Search Console's own Performance report is the baseline until there is traffic worth a second tool | — | — |

What I need from you to take the code side further: read access to the Search
Console property once it exists (impressions/clicks by page are the baseline
the ledger needs), and a yes/no on entity hub pages (`/entity/<slug>`, audit
H29) — the cast chips currently link to `/search`, which is `noindex`, so no
topical authority accrues anywhere.

## Indexing audit, 2026-09-27

Search Console (snapshot of 2026-09-21, the day of the SEO release): 36 known
pages, 4 indexed, 0 impressions; 29 "Crawled - currently not indexed", 3 "Page
with redirect". `tools/seo_crawl_audit.py` fetches our sitemaps' URLs as
Googlebot and checks the signals we control:

- **Page with redirect (3)** are the three host variants (`http://readprism.news`,
  `https://readprism.news`, `http://www.readprism.news`) moving to
  `https://www.readprism.news`. Correct, nothing to fix (the http apex takes two
  hops; Google follows them).
- **No sitemap URL** redirected, errored, named another canonical or was
  `noindex` (476 URLs checked: all of sitemap.xml and the news sitemap, a
  sample of records and actors).
- **Fixed:** `/subject/<group>` for the six sector groups listed exactly the
  records `/sector/<group>` did (30 of 30, same title). It now names the sector
  page as canonical and is out of the sitemap (`sectorPageFor`). Education,
  Civic and deeper subject nodes are unchanged.
- **Fixed:** actor pages in three records were thin (28 of the 29 thin ones);
  the indexing floor is four records now.
- **Fixed:** `/pulse` (26 words to a crawler) is out of the sitemap and `noindex`.
- Records are not thin (0 of 250, median 465 words), nor are stories (316) or
  subject pages (1,198). What remains is the site's age and duplicate records
  (about 10%, which the verified matching tier addresses).

**The 29 URLs Google skipped** (drilldown export, crawled 2026-09-22; `tools/seo_crawl_audit.py --urls`)
all pass every technical check today. What they share is content:

- 19 records: 13 from **one outlet** (a rewrite of one article, which Google
  keeps instead), 3 from two; several are **duplicates of another record** of
  ours (the Tamil Nadu breakfast scheme twice, cos 0.93, both skipped; Tata Sons
  twice; the IIT Bombay death across 4-5 records).
- 4 stories: all **provisional**, and each had drifted from its own URL
  (`/trending/how-did-bmw-crash-on-mumbai-coastal-road-…` titled "President
  confers National Film Awards").
- `/feed`, `/sector/politics`, `/plus`, `/terms`, `/privacy`, `/refunds`: listing
  and policy pages; commonly not indexed early, nothing to do.

**Fixed (0.0.105.0):** a record asks to be indexed from its second outlet on
(`common/outlets.record_indexable`, counted by publisher as the page prints it),
and a story once its boundary is verified (`common/stories.STORY_BOUNDARY_STATUS`,
provisional for all today). Both stay readable and linked (`noindex, follow`,
`lib/seo.NOT_INDEXED`); the record page, its quote pages, the feed rows, all
three sitemaps and IndexNow read the same rule. The records sitemap went from
~26k URLs to the multi-outlet ~3.6k. The duplicates need the verified matching
tier live, then the backlog merge with 308s.

Rerun after a change: `uv run python -m tools.seo_crawl_audit --csv .context/review/seo-crawl.csv`.
For the URLs Google itself skipped, export Pages → "Crawled - currently not
indexed" from Search Console.

## How to check it is working

```
curl -sA "Mozilla/5.0 (compatible; OAI-SearchBot/1.0)" https://www.readprism.news/feed | grep -c row-card   # 60
curl -s https://www.readprism.news/story/00000000-0000-0000-0000-000000000000 -o /dev/null -w "%{http_code}\n"   # 404, not 200
curl -s https://www.readprism.news/about | sed 's#</head>.*##' | grep -c 'rel="canonical"'   # 1: metadata in <head>
curl -s https://www.readprism.news/news-sitemap.xml | grep -c "<news:news>"
curl -s https://www.readprism.news/llms.txt | head -3
```

Google's Rich Results Test (search.google.com/test/rich-results) on a `/story/<id>`
URL should show one NewsArticle with no errors; the Schema validator
(validator.schema.org) will show the `isBasedOn` list. Search Console →
Sitemaps shows both files discovered; Bing Webmaster → IndexNow shows the hourly
batches.
