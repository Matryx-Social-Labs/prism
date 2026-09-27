"""What a search crawler finds at the URLs our sitemaps hand it. Read-only.

Search Console, 2026-09-21: 36 known pages, 4 indexed; 29 "Crawled - currently
not indexed" and 3 "Page with redirect". Google does not say why per URL, but
it discounts pages that send mixed signals, so this checks every sitemap URL
for the ones we control:

  - status: anything but 200 (a redirect or error listed in a sitemap)
  - canonical: the page names a different URL as the original
  - robots: a noindex page listed in a sitemap
  - thin: little visible text beyond the site's own furniture
  - duplicate titles across different URLs
  - host variants: every other form of the domain reaches https://www in one hop

  uv run python -m tools.seo_crawl_audit                    # sitemap.xml + news, 150 records, 100 entities
  uv run python -m tools.seo_crawl_audit --records 400 --entities 300 --csv .context/review/seo-crawl.csv
  uv run python -m tools.seo_crawl_audit --urls ~/Downloads/<GSC drilldown>/Table.csv   # the URLs Google skipped
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import random
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

SITE = "https://www.readprism.news"
UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
THIN_WORDS = 150  # visible words below which a page reads as thin to a ranker
HOST_VARIANTS = ["http://readprism.news/", "https://readprism.news/", "http://www.readprism.news/"]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_a, **_k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _get(url: str) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with _opener.open(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), ""


def sitemap_urls(path: str) -> list[str]:
    _, _, body = _get(f"{SITE}{path}")
    return re.findall(r"<loc>([^<]+)</loc>", body)


@dataclass
class Page:
    url: str
    status: int
    location: str = ""
    canonical: str = ""
    robots: str = ""
    title: str = ""
    words: int = 0
    problems: str = ""


def _text_words(html: str) -> int:
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<header.*?</header>|<footer.*?</footer>|<nav.*?</nav>", " ", html, flags=re.S)
    return len(re.sub(r"<[^>]+>", " ", body).split())


def audit(url: str) -> Page:
    status, headers, html = _get(url)
    page = Page(url=url, status=status, location=headers.get("Location") or headers.get("location") or "")
    if status == 200:
        pick = lambda p: (re.search(p, html, re.S) or [None, ""])[1]  # noqa: E731
        page.canonical = pick(r'<link rel="canonical" href="([^"]*)"')
        page.robots = pick(r'<meta name="robots" content="([^"]*)"')
        page.title = pick(r"<title>(.*?)</title>")
        page.words = _text_words(html)
    problems = []
    if status != 200:
        problems.append(f"status {status}" + (f" -> {page.location}" if page.location else ""))
    else:
        if page.canonical and page.canonical.rstrip("/") != url.rstrip("/"):
            problems.append("canonical elsewhere")
        if not page.canonical:
            problems.append("no canonical")
        if "noindex" in page.robots:
            problems.append("noindex in a sitemap")
        if page.words < THIN_WORDS:
            problems.append(f"thin ({page.words} words)")
    page.problems = "; ".join(problems)
    return page


def host_variants() -> list[str]:
    lines = []
    for v in HOST_VARIANTS:
        status, headers, _ = _get(v)
        loc = headers.get("Location") or headers.get("location") or ""
        hop_status = _get(loc)[0] if loc.startswith("http") else None
        ok = status in (301, 308) and loc.rstrip("/") == SITE and hop_status == 200
        lines.append(f"{'ok ' if ok else 'BAD'} {v} -> {status} {loc} -> {hop_status}")
    return lines


def _listed(path: Path) -> list[str]:
    return [line.split(",")[0].strip() for line in path.read_text().splitlines() if line.startswith("http")]


def report(pages: list[Page], out: Path | None) -> None:
    by_kind = collections.Counter()
    for p in pages:
        for prob in filter(None, p.problems.split("; ")):
            by_kind[re.sub(r"\(\d+ words\)| -> .*|\d{3}", "", prob).strip()] += 1
    titles = collections.defaultdict(list)
    for p in pages:
        if p.title:
            titles[p.title].append(p.url)
    dup_titles = {t: us for t, us in titles.items() if len(us) > 1}

    print(f"{len(pages)} URLs · {sum(1 for p in pages if not p.problems)} clean")
    for kind, n in by_kind.most_common():
        print(f"  {n:>4}  {kind}")
    print(f"  {sum(len(u) for u in dup_titles.values()):>4}  share a title with another URL ({len(dup_titles)} titles)")
    print("\nexamples:")
    shown = collections.Counter()
    for p in pages:
        if p.problems:
            kind = p.problems.split(";")[0]
            key = re.sub(r"\(\d+ words\)| -> .*|\d{3}", "", kind).strip()
            if shown[key] < 3:
                shown[key] += 1
                print(f"  {p.url.replace(SITE, '')[:70]:<70}  {p.problems}")
    for t, us in list(dup_titles.items())[:3]:
        print(f"  same title {t[:60]!r}: {', '.join(u.replace(SITE, '') for u in us[:3])}")
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(pages[0])))
            w.writeheader()
            w.writerows(asdict(p) for p in pages)
        print(f"\nwrote {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--records", type=int, default=150, help="records sampled from records-sitemap.xml")
    ap.add_argument("--entities", type=int, default=100, help="actors sampled from entities-sitemap.xml")
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--urls", type=Path, help="audit these URLs instead (first column; a Search Console export works)")
    args = ap.parse_args()
    if args.urls:
        report([audit(u) for u in _listed(args.urls)], args.csv)
        return

    rng = random.Random(7)
    sets = {
        "sitemap.xml": sitemap_urls("/sitemap.xml"),
        "news-sitemap.xml": sitemap_urls("/news-sitemap.xml"),
        "records-sitemap.xml": sitemap_urls("/records-sitemap.xml"),
        "entities-sitemap.xml": sitemap_urls("/entities-sitemap.xml"),
    }
    sample = {
        "sitemap.xml": sets["sitemap.xml"],
        "news-sitemap.xml": sets["news-sitemap.xml"],
        "records-sitemap.xml": rng.sample(sets["records-sitemap.xml"], min(args.records, len(sets["records-sitemap.xml"]))),
        "entities-sitemap.xml": rng.sample(sets["entities-sitemap.xml"], min(args.entities, len(sets["entities-sitemap.xml"]))),
    }
    urls = sorted({u for us in sample.values() for u in us})
    print("sitemaps: " + ", ".join(f"{k} {len(v)} URLs" for k, v in sets.items()))
    print(f"auditing {len(urls)} distinct URLs (all of sitemap.xml + news, a sample of records and entities)\n")
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        pages = list(pool.map(audit, urls))

    report(pages, None)
    print("\nhost variants:")
    for line in host_variants():
        print("  " + line)
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(pages[0])))
            w.writeheader()
            w.writerows(asdict(p) for p in pages)
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
