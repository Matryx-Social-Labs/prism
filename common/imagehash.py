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

import httpx

from common.logging import get_logger

logger = get_logger(__name__)

MAX_BYTES = 3 * 1024 * 1024
UA = "Mozilla/5.0 (compatible; Prism/1.0; +https://readprism.news)"


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
    http = http or httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0), follow_redirects=True)
    try:
        async with http.stream("GET", url, headers={"User-Agent": UA}) as r:
            if r.status_code != 200:
                return None
            buf = bytearray()
            async for chunk in r.aiter_bytes(64 * 1024):
                buf.extend(chunk)
                if len(buf) > MAX_BYTES:
                    return None
        return dhash_bytes(bytes(buf))
    except Exception as exc:  # noqa: BLE001
        logger.debug("image_hash_failed", url=url[:120], error=str(exc)[:80])
        return None
    finally:
        if own:
            await http.aclose()
