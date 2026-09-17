"""Conservative, versioned URL identity for article deduplication.

The source URL remains untouched on ``raw_items.url`` for provenance.  This
module produces a comparison key only: tracking decoration is removed, fragments
are ignored, and HTTP/HTTPS/default-port spelling is normalised.  Unknown query
parameters are preserved because a news site may use them to select the article.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CANONICAL_URL_VERSION = 1

_TRACKING_KEYS = frozenset({
    "_ga", "at_campaign", "at_link_id", "at_medium", "at_ptr_name", "dclid",
    "fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "msclkid",
})


def _is_tracking_key(key: str) -> bool:
    folded = key.casefold()
    return folded.startswith("utm_") or folded in _TRACKING_KEYS


def canonicalize_url(url: str | None) -> str | None:
    """Return a stable article identity key, or ``None`` for no usable URL.

    Deliberately not included: AMP/mobile host rewriting, arbitrary ``ref``
    removal, path case folding, percent-decoding, or publisher-specific slug
    surgery.  Each can merge two real documents and belongs behind measured,
    explicit alias rules rather than a generic cleaner.
    """
    raw = (url or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return raw
        # Credentials in feed URLs are unexpected. Preserve the observation but
        # decline to reinterpret it as a canonical public article address.
        if parsed.username is not None or parsed.password is not None:
            return raw

        host = parsed.hostname.casefold().rstrip(".")
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            return raw
        port = parsed.port
        netloc = host if port in (None, 80, 443) else f"{host}:{port}"

        query = [
            (key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not _is_tracking_key(key)
        ]
        # Query order is not document identity. Repeated parameters are retained.
        query.sort(key=lambda pair: (pair[0], pair[1]))
        path = parsed.path or "/"
        return urlunsplit(("https", netloc, path, urlencode(query, doseq=True), ""))
    except (ValueError, UnicodeError):
        # A malformed publisher URL is still provenance. Returning it unchanged
        # preserves today's exact-match behaviour instead of dropping the key.
        return raw
