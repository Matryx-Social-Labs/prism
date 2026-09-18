"""Write the token block of web/src/app/globals.css from design/tokens.json.

    uv run python design/gen_css.py          # rewrites the block between the markers
    uv run python design/gen_css.py --check  # exit 1 if globals.css is stale (CI)

tokens.json is the single source for the web and the future React Native theme;
nobody edits the generated block by hand. Old variable names from the Reservation
Chart (--bg-elevated, --ink-muted, --lens-finance …) are kept as aliases so a
component that has not been rebuilt yet still paints in the new world.
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

# Reservation Chart names → Spectrum roles. Deleted when the last reader goes.
ALIASES = {
    "bg-elevated": "var(--surface)",
    "bg-sunken": "var(--sunken)",
    "ink-muted": "var(--ink-2)",
    "ink-faint": "var(--ink-3)",
    "lens-general": "var(--ink)",  # the Reader lens is neutral now
    "lens-general-bg": "var(--sunken)",
    "lens-finance": "var(--lens-markets)",
    "lens-finance-bg": "var(--lens-markets-soft)",
    "lens-cyber-bg": "var(--lens-cyber-soft)",
    "danger-bg": "color-mix(in srgb, var(--danger) 12%, transparent)",
    "up-bg": "color-mix(in srgb, var(--up) 12%, transparent)",
    "glass": "color-mix(in srgb, var(--bg) 88%, transparent)",
    "shadow-card": "var(--shadow-1)",
    "shadow-pop": "var(--shadow-2)",
    "scrim": "rgba(15, 15, 18, 0.45)",
    "app-header-h": "52px",
}


def block(t: dict, mode: str) -> str:
    lines = [f"  --{k}: {v['value']};" for k, v in t["color"][mode].items()]
    if mode == "light":
        lines += [f"  --{k}: {v};" for k, v in ALIASES.items()]
        lines += [
            f"  --shadow-1: {t['shadow']['1']};",
            f"  --shadow-2: {t['shadow']['2']};",
            "  --spectrum: linear-gradient(90deg, " + ", ".join(t["color"]["spectrum"]["stops"]) + ");",
            f"  --ease: {t['motion']['standard']['easing']};",
            f"  --t-micro: {t['motion']['micro']['ms']}ms;",
            f"  --t-std: {t['motion']['standard']['ms']}ms;",
            f"  --shell: {t['layout']['shell']}px;",
            f"  --reading: {t['layout']['reading']}px;",
            f"  --rail: {t['layout']['rail']}px;",
            f"  --topbar: {t['layout']['topbar']}px;",
            f"  --tabbar: {t['layout']['tabbar']}px;",
        ]
        lines += [f"  --r-{k}: {v}px;" for k, v in t["radius"].items()]
    else:
        lines += [
            "  --shadow-1: 0 1px 2px rgba(0, 0, 0, 0.4);",
            "  --shadow-2: 0 12px 32px -8px rgba(0, 0, 0, 0.6), 0 2px 6px rgba(0, 0, 0, 0.3);",
        ]
    return "\n".join(lines)


def render(t: dict) -> str:
    light, dark = block(t, "light"), block(t, "dark")
    return f"""{BEGIN}
:root,
:root[data-theme="light"] {{
  color-scheme: light;
{light}
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
{dark}
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
{dark}
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
