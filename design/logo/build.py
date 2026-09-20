"""Export the Prism mark as PNGs, from the same numbers as web/src/lib/mark.ts.

    uv run python design/logo/build.py

Writes design/logo/exports/ (mark on transparent, on ivory, on charcoal; the
lockup with the wordmark) and copies the shareable set to web/public/brand/.
Drawn at 16× and downsampled, so edges are clean at every size.
"""
from __future__ import annotations

import math
import pathlib
import shutil

from PIL import Image, ImageDraw, ImageFont

BOX = 24
APEX_Y = 19 - 20 * math.sqrt(3) / 2  # 1.68
TRI = [(12, APEX_Y), (22, 19), (2, 19)]
BAND = (2, 20.25, 20, 2.75)
SPECTRUM = ["#ef4444", "#f59e0b", "#06b6d4", "#8b5cf6"]
INK, IVORY, CHARCOAL = "#141414", "#f2f4ee", "#141414"
OUT = pathlib.Path(__file__).with_name("exports")
PUBLIC = pathlib.Path(__file__).parents[2] / "web" / "public" / "brand"


def mark(px: int, ink: str, bg: str | None, pad_ratio: float = 0.0) -> Image.Image:
    ss = 16
    size = px * ss
    im = Image.new("RGBA", (size, size), bg if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = pad_ratio * BOX
    scale = size / (BOX + 2 * pad)
    off = pad * scale
    tri = [(off + x * scale, off + y * scale) for x, y in TRI]
    d.polygon(tri, fill=ink)
    bx, by, bw, bh = BAND
    seg = bw / len(SPECTRUM)
    for i, c in enumerate(SPECTRUM):
        x0 = off + (bx + i * seg) * scale
        x1 = off + (bx + (i + 1) * seg) * scale
        d.rectangle([x0, off + by * scale, x1, off + (by + bh) * scale], fill=c)
    return im.resize((px, px), Image.Resampling.LANCZOS)


def lockup(height: int, ink: str, bg: str | None) -> Image.Image:
    """Mark + 'Prism' in Newsreader if available, else the system serif."""
    m = mark(height, ink, None)
    font = None
    for cand in ["/System/Library/Fonts/Supplemental/Georgia.ttf", "/Library/Fonts/Georgia.ttf"]:
        try:
            font = ImageFont.truetype(cand, int(height * 0.92))
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    text = "Prism"
    tw = int(font.getlength(text))
    gap = int(height * 0.42)
    im = Image.new("RGBA", (height + gap + tw + int(height * 0.1), height), bg if bg else (0, 0, 0, 0))
    im.alpha_composite(m, (0, 0))
    ImageDraw.Draw(im).text((height + gap, height * 0.5), text, font=font, fill=ink, anchor="lm")
    return im


def main() -> None:
    OUT.mkdir(exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for px in (16, 32, 48, 64, 128, 180, 192, 256, 512, 1024):
        mark(px, INK, None).save(OUT / f"prism-mark-{px}.png")
    mark(1024, INK, IVORY, pad_ratio=0.12).save(OUT / "prism-mark-1024-ivory.png")
    mark(1024, IVORY, CHARCOAL, pad_ratio=0.12).save(OUT / "prism-mark-1024-charcoal.png")
    # App-icon style: on ivory with generous padding (Play/App Store crop the corners).
    mark(1024, INK, IVORY, pad_ratio=0.18).save(OUT / "prism-app-icon-1024.png")
    lockup(160, INK, None).save(OUT / "prism-lockup-ink.png")
    lockup(160, INK, IVORY).save(OUT / "prism-lockup-ivory.png")
    lockup(160, IVORY, CHARCOAL).save(OUT / "prism-lockup-charcoal.png")
    for name in ("prism-mark-512.png", "prism-mark-1024-ivory.png", "prism-mark-1024-charcoal.png", "prism-app-icon-1024.png", "prism-lockup-ivory.png", "prism-lockup-charcoal.png"):
        shutil.copy(OUT / name, PUBLIC / name)
    print("wrote", len(list(OUT.iterdir())), "files to", OUT, "and", len(list(PUBLIC.iterdir())), "to", PUBLIC)


if __name__ == "__main__":
    main()
