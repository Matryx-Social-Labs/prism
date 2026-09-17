from common.urls import CANONICAL_URL_VERSION, canonicalize_url


def test_version_is_explicit_so_backfills_are_reproducible():
    assert CANONICAL_URL_VERSION == 1


def test_tracking_and_fragments_do_not_create_new_articles():
    a = "http://News.Example/story?id=42&utm_source=rss&fbclid=abc#comments"
    b = "https://news.example:443/story?fbclid=other&id=42"
    assert canonicalize_url(a) == canonicalize_url(b) == "https://news.example/story?id=42"


def test_bbc_adobe_campaign_parameters_are_tracking_not_identity():
    assert canonicalize_url(
        "https://www.bbc.com/hindi/articles/abc?at_medium=RSS&at_campaign=rss"
    ) == "https://www.bbc.com/hindi/articles/abc"


def test_unknown_query_parameters_are_preserved_and_sorted():
    assert canonicalize_url("https://example.test/a?edition=ka&id=2") == (
        "https://example.test/a?edition=ka&id=2"
    )
    assert canonicalize_url("https://example.test/a?id=2&edition=ka") == (
        "https://example.test/a?edition=ka&id=2"
    )


def test_semantic_query_values_remain_distinct():
    assert canonicalize_url("https://example.test/a?id=1") != canonicalize_url(
        "https://example.test/a?id=2"
    )


def test_non_http_and_malformed_urls_keep_exact_match_semantics():
    assert canonicalize_url("urn:cve:CVE-2026-1234") == "urn:cve:CVE-2026-1234"
    assert canonicalize_url(None) is None
    assert canonicalize_url("  ") is None
