"""A migration that builds an index CONCURRENTLY must manage lock_timeout itself.

Every migration connects with lock_timeout 5 s (db/README.md). A concurrent build
that times out leaves an INVALID index that `IF NOT EXISTS` then skips for good.
"""

from pathlib import Path

VERSIONS = Path(__file__).resolve().parent.parent / "db" / "versions"

# Written before the migration lock_timeout existed, and already applied in production.
GRANDFATHERED = {
    "51de411d824c_perf_indexes_fk_hot_paths_pgvector_hnsw.py",
    "5493a4141cbb_multilingual_embeddings_384_768_events_.py",
    "a7d4e2c19b60_enrichments_article_index.py",
    "b17e4c9a2f31_index_event_memberships_article.py",
    "b4d18e7c3f20_subject_path.py",
    "c8a3f5d21b74_search_trgm_index.py",
    "f7d3b9c2e481_articles_gist_hnsw.py",
}


def test_every_concurrent_index_build_sets_its_own_lock_timeout():
    offenders = sorted(
        f.name
        for f in VERSIONS.glob("*.py")
        if f.name not in GRANDFATHERED and "CONCURRENTLY" in (text := f.read_text()) and "lock_timeout" not in text
    )
    assert offenders == [], f"add SET lock_timeout = 0 / RESET lock_timeout (db/README.md): {offenders}"
