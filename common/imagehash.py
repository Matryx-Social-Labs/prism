"""A perceptual fingerprint for a report's photo, so two uploads of one picture
read as one picture.

BBC's Tamil, Telugu and Bengali editions each upload the same photograph under
a new id, so no URL check can see the repeat; a reader saw the same face three
times in a story's rail (2026-09-20). dHash: shrink to 9×8 greyscale, compare
each pixel with its right neighbour, 64 bits. Two crops or re-encodes of one
photo land within a few bits of each other; two different photos almost never
do. The image is fetched once, small, and discarded — Prism never stores or
serves it (DESIGN.md § Images).
"""
from __future__ import annotations

import io
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from common.logging import get_logger

logger = get_logger(__name__)

MAX_BYTES = 3 * 1024 * 1024
MAX_HOPS = 3
UA = "Mozilla/5.0 (compatible; Prism/1.0; +https://readprism.news)"


def public_http_url(url: str) -> bool:
    """True only for an http(s) URL whose host resolves entirely to public
    addresses. The URL comes from a publisher's feed or page metadata, which a
    compromised feed controls, and the worker fetches it from inside the
    deployment — so loopback, private, link-local (cloud metadata) and any
    non-http scheme are refused before a socket is opened."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return False
    return True


def dhash_bytes(data: bytes) -> str | None:
    """64-bit difference hash as 16 hex chars, or None if the bytes are not an image."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            px = list(im.getdata())
    except Exception:  # noqa: BLE001 — not an image, or a broken one: no hash
        return None
    bits = 0
    for row in range(8):
        for col in range(8):
            left, right = px[row * 9 + col], px[row * 9 + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


async def fetch_dhash(url: str, http: httpx.AsyncClient | None = None) -> str | None:
    """Fetch the image (bounded) and hash it. None on any failure — a photo
    without a hash is simply shown as before."""
    own = http is None
    # Redirects are followed by hand so every hop passes the same address check.
    http = http or httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0), follow_redirects=False)
    try:
        for _ in range(MAX_HOPS + 1):
            if not public_http_url(url):
                logger.info("image_hash_refused", url=url[:120])
                return None
            async with http.stream("GET", url, headers={"User-Agent": UA}, follow_redirects=False) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    url = str(r.url.join(r.headers["location"]))
                    continue
                if r.status_code != 200:
                    return None
                buf = bytearray()
                async for chunk in r.aiter_bytes(64 * 1024):
                    buf.extend(chunk)
                    if len(buf) > MAX_BYTES:
                        return None
            return dhash_bytes(bytes(buf))
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("image_hash_failed", url=url[:120], error=str(exc)[:80])
        return None
    finally:
        if own:
            await http.aclose()
