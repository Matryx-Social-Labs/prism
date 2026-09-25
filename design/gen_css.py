"""Write the token block of web/src/app/globals.css from design/tokens.json.

    uv run python design/gen_css.py          # rewrites the block between the markers
    uv run python design/gen_css.py --check  # exit 1 if globals.css is stale (CI)

tokens.json is the single source for the web and the future React Native theme;
nobody edits the generated block by hand.

Fonts: next/font puts one variable per family on <html> (web/src/app/layout.tsx),
named --font-<family-slug>. The voice stacks below are declared on :root, the same
element, so they resolve (a custom property resolves where it is declared — a stack
on :root that referenced variables living on <body> computed to nothing once).

Aliases keep two vocabularies painting: the v2 design-system names the Claude
Design components use (--paper, --cov-*, --link …) and the older names components
that were not rebuilt still read (--bg-elevated, --ink-muted …).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "design" / "tokens.json"
CSS = ROOT / "web" / "src" / "app" / "globals.css"
BEGIN = "/* ── tokens:begin — generated from design/tokens.json by design/gen_css.py; do not edit ── */"
END = "/* ── tokens:end ── */"

GENERIC = {"serif", "sans-serif", "monospace", "system-ui", "ui-monospace", "Georgia", "SFMono-Regular", "Menlo"}

ALIASES = {
    # v2 design-system names
    "paper": "var(--bg)",
    "cov-national": "var(--coverage-national)",
    "cov-intl": "var(--coverage-intl)",
    "cov-regional": "var(--coverage-regional)",
    "cov-wire": "var(--coverage-wire)",
    "text-body": "var(--ink)",
    "text-secondary": "var(--ink-2)",
    "text-provenance": "var(--ink-3)",
    "surface-card": "var(--surface)",
    "surface-sheet": "var(--elevated)",
    "surface-well": "var(--sunken)",
    "border-hairline": "var(--line)",
    "border-control": "var(--line-strong)",
    "link": "var(--accent)",
    "link-hover": "var(--accent-strong)",
    "focus-ring": "var(--accent)",
    # older names
    "bg-elevated": "var(--surface)",
    "bg-sunken": "var(--sunken)",
    "ink-muted": "var(--ink-2)",
    "ink-faint": "var(--ink-3)",
    "lens-general": "var(--ink)",
    "lens-general-bg": "var(--sunken)",
    "lens-finance": "var(--lens-markets)",
    "lens-finance-bg": "var(--lens-markets-soft)",
    "lens-cyber-bg": "var(--lens-cyber-soft)",
    "danger-bg": "var(--danger-soft)",
    "up-bg": "color-mix(in srgb, var(--up) 12%, transparent)",
    "glass": "color-mix(in srgb, var(--bg) 92%, transparent)",
    "shadow-card": "var(--shadow-1)",
    "shadow-pop": "var(--shadow-2)",
    "app-header-h": "var(--masthead)",
    "font-display": "var(--font-record)",
    "font-ui": "var(--font-read)",
}


def slug(family: str) -> str:
    return "--font-" + family.lower().replace(" ", "-")


def stack(spec: dict) -> str:
    fams = [spec["family"], *spec["fallback"]]
    return ", ".join(f if f in GENERIC else f"var({slug(f)})" for f in fams)


def colors(t: dict, mode: str) -> list[str]:
    return [f"  --{k}: {v['value']};" for k, v in t["color"][mode].items()]


def type_scale(t: dict, i: int) -> list[str]:
    out = []
    for k, s in t["type"].items():
        style = "italic " if s.get("style") == "italic" else ""
        out.append(f"  --t-{k}: {style}{s['weight']} {s['size'][i]}px/{s['line'][i]} var(--font-{s['font']});")
    return out


def light(t: dict) -> str:
    m, lay = t["motion"], t["layout"]
    lines = colors(t, "light")
    lines += aliases()
    lines += [f"  --font-{k}: {stack(v)};" for k, v in t["font"].items()]
    lines += type_scale(t, 0)
    lines += [f"  --track-{k}: {v};" for k, v in t["tracking"].items()]
    lines += [f"  --s-{k}: {v}px;" for k, v in t["space"].items()]
    lines += [f"  --r-{k}: {v}px;" for k, v in t["radius"].items()]
    lines += [f"  --rule-{k}: {v}px;" for k, v in t["rule"].items()]
    lines += [
        f"  --shadow-1: {t['shadow']['1']};",
        f"  --shadow-2: {t['shadow']['2']};",
        "  --spectrum: linear-gradient(90deg, " + ", ".join(t["color"]["spectrum"]["stops"]) + ");",
        f"  --ease: {m['standard']['easing']};",
        f"  --ease-flip: {m['flip']['easing']};",
        f"  --t-micro: {m['micro']['ms']}ms;",
        f"  --t-std: {m['standard']['ms']}ms;",
        f"  --t-flip-min: {m['flip']['min_ms']}ms;",
        f"  --t-flip-max: {m['flip']['max_ms']}ms;",
    ]
    lines += [f"  --{k}: {lay[k]}px;" for k in ("shell", "reading", "rail", "evidence", "topbar", "masthead", "tabbar", "touch")]
    lines.append(f"  --gutter: {lay['gutter'][0]}px;")
    return "\n".join(lines)


def aliases() -> list[str]:
    return [f"  --{k}: {v};" for k, v in ALIASES.items()]


def dark(t: dict) -> str:
    return "\n".join(colors(t, "dark") + [
        f"  --shadow-1: {t['shadow']['dark-1']};",
        f"  --shadow-2: {t['shadow']['dark-2']};",
    ])


def scoped(t: dict, mode: str) -> str:
    """A theme on ANY element (a dark section on a light page, and back): the colours and,
    re-declared, every alias — an alias resolves where it is declared, so the :root copy
    would carry the page's theme into the section."""
    extra = [f"  --shadow-1: {t['shadow']['dark-1']};", f"  --shadow-2: {t['shadow']['dark-2']};"] if mode == "dark" else [
        f"  --shadow-1: {t['shadow']['1']};", f"  --shadow-2: {t['shadow']['2']};"]
    return "\n".join(colors(t, mode) + aliases() + extra)


def render(t: dict) -> str:
    lay = t["layout"]
    desk = "\n".join("  " + l for l in type_scale(t, 1))
    d = dark(t)
    return f"""{BEGIN}
:root,
:root[data-theme="light"] {{
  color-scheme: light;
{light(t)}
}}
@media (min-width: 640px) {{ :root {{ --gutter: {lay['gutter'][1]}px; }} }}
@media (min-width: 1024px) {{
  :root {{
    --gutter: {lay['gutter'][2]}px;
{desk}
  }}
}}
@media (min-width: {lay['wide']['min']}px) {{ :root {{ --shell: {lay['wide']['shell']}px; --rail: {lay['wide']['rail']}px; --evidence: {lay['wide']['evidence']}px; }} }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
{d}
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
{d}
}}
/* A theme set on an element below the root (the landing's dark section). */
:root [data-theme="dark"] {{
  color-scheme: dark;
{scoped(t, "dark")}
}}
:root [data-theme="light"] {{
  color-scheme: light;
{scoped(t, "light")}
}}
{END}"""


def main() -> int:
    t = json.loads(TOKENS.read_text())
    css = CSS.read_text()
    a, b = css.find(BEGIN), css.find(END)
    if a < 0 or b < 0:
        print("markers not found in globals.css", file=sys.stderr)
        return 2
    new = css[:a] + render(t) + css[b + len(END):]
    if "--check" in sys.argv:
        if new != css:
            print("globals.css token block is stale — run: uv run python design/gen_css.py", file=sys.stderr)
            return 1
        return 0
    CSS.write_text(new)
    print("wrote token block →", CSS.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
