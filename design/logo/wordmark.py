"""The press kit's logo files: the readPrism.news lockup and the mark, SVG and PNG,
for light and dark grounds (web/public/brand/, listed on /press).

    curl -sSLo /tmp/Newsreader.ttf \
      "https://github.com/google/fonts/raw/main/ofl/newsreader/Newsreader%5Bopsz,wght%5D.ttf"
    uv run --no-project --with fonttools --with uharfbuzz --with cairosvg \
      python design/logo/wordmark.py /tmp/Newsreader.ttf

Nothing is drawn here. The mark is lib/mark.ts's numbers (as build.py and
PrismMark use them) and the lockup is components/Brand.tsx set in outlines, so
the file holds without the font: the mark, then readPrism.news in Newsreader,
"read" and ".news" at 400 in ink-3, "Prism" at 600 in ink, 0.95 x the mark,
-0.01em tracking, 0.42 x the mark from it, the text centred on the mark's box
at line-height 1 as the header sets it (DESIGN.md, The wordmark). The optical
size is the one the desktop bar renders at (mark 24, text 23px). Colours are
the v2 tokens (design/tokens.json): ink and ink-3, light and dark. Transparent
grounds; each file is named for the ground it goes on.
"""
from __future__ import annotations

import math
import pathlib
import sys

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen

BOX = 24
TRIANGLE = f"M12 {19.5 - 20 * math.sqrt(3) / 2:.2f} L22 19.5 L2 19.5 Z"  # "M12 2.18 L22 19.5 L2 19.5 Z"
BAND = 'x="2" y="19.5" width="20" height="2.75"'
SPECTRUM = ["#ef4444", "#f59e0b", "#06b6d4", "#8b5cf6"]
GROUNDS = {"on-light": ("#111317", "#5B6069"), "on-dark": ("#F2F1ED", "#9A9FA8")}  # (ink, ink-3)
TEXT_SIZE = 0.95 * BOX
GAP = 0.42 * BOX
TRACKING = -0.01 * TEXT_SIZE
OPSZ = 23
PNG_HEIGHT = 192  # px; the SVGs are the masters
PUBLIC = pathlib.Path(__file__).parents[2] / "web" / "public" / "brand"


def gradient() -> str:
    stops = "".join(f'<stop offset="{i / (len(SPECTRUM) - 1):.4f}" stop-color="{c}"/>' for i, c in enumerate(SPECTRUM))
    return f'<defs><linearGradient id="spectrum" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient></defs>'


def mark(ink: str) -> str:
    return f'<path d="{TRIANGLE}" fill="{ink}"/><rect {BAND} fill="url(#spectrum)"/>'


def run(face: hb.Face, text: str, weight: int, x: float, baseline: float, fill: str) -> tuple[str, float]:
    """One run of the wordmark in outlines, shaped (kerning included) at its weight; returns the path and the pen's x after it."""
    font = hb.Font(face)
    font.set_variations({"wght": weight, "opsz": OPSZ})
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    scale = TEXT_SIZE / face.upem
    paths = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        pen = SVGPathPen(None)
        font.draw_glyph_with_pen(info.codepoint, pen)
        d = pen.getCommands()
        if d:
            gx, gy = x + pos.x_offset * scale, baseline - pos.y_offset * scale
            paths.append(f'<path transform="translate({gx:.3f} {gy:.3f}) scale({scale:.6f} {-scale:.6f})" d="{d}"/>')
        x += pos.x_advance * scale + TRACKING
    return f'<g fill="{fill}">{"".join(paths)}</g>', x


def lockup(face: hb.Face, ink: str, quiet: str) -> str:
    font = hb.Font(face)
    font.set_variations({"wght": 400, "opsz": OPSZ})
    ext = font.get_font_extents("ltr")
    scale = TEXT_SIZE / face.upem
    # line-height 1, centred on the mark's box: the content area sits in the
    # middle of a line box one em tall, and the baseline is its ascent down.
    content = (ext.ascender - ext.descender) * scale
    baseline = (BOX - TEXT_SIZE) / 2 + (TEXT_SIZE - content) / 2 + ext.ascender * scale
    x = BOX + GAP
    parts = []
    for text, weight, fill in (("read", 400, quiet), ("Prism", 600, ink), (".news", 400, quiet)):
        svg, x = run(face, text, weight, x, baseline, fill)
        parts.append(svg)
    width = math.ceil(x - TRACKING)  # the tracking after the last letter is not ink
    return svg_doc(width, f"{mark(ink)}{''.join(parts)}")


def svg_doc(width: float, body: str, title: str = "readPrism.news") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {BOX}" width="{width * 8}" height="{BOX * 8}">'
            f"<title>{title}</title>{gradient()}{body}</svg>\n")


def main(font_path: str) -> None:
    face = hb.Face(pathlib.Path(font_path).read_bytes())
    for ground, (ink, quiet) in GROUNDS.items():
        files = {f"readprism-lockup-{ground}": lockup(face, ink, quiet), f"prism-mark-{ground}": svg_doc(BOX, mark(ink), "Prism")}
        for name, svg in files.items():
            (PUBLIC / f"{name}.svg").write_text(svg)
            cairosvg.svg2png(bytestring=svg.encode(), write_to=str(PUBLIC / f"{name}.png"), output_height=PNG_HEIGHT if "lockup" in name else 1024)
            print("wrote", PUBLIC / f"{name}.svg", "and .png")


if __name__ == "__main__":
    main(sys.argv[1])
