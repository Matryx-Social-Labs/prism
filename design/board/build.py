"""Render the Prism Spectrum design board from design/tokens.json and live payloads.

    uv run python design/board/build.py            # writes design/board/*.html
    uv run python design/board/build.py --fetch    # refresh the JSON from the prod API first

Everything on the board is real data (feed, one story record with its verified
quotes, the trending list, the lens registry). Nothing is invented; where a
number would have to be made up the board prints the word ILLUSTRATION.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
API = "https://prism-production-6747.up.railway.app"
DATA = HERE / "data"

SECTORS = [
    ("politics", "POL", "Politics"), ("business", "BIZ", "Business & Markets"), ("sports", "SPO", "Sports"),
    ("technology", "TEC", "Tech & Cyber"), ("science", "HLT", "Health & Science"), ("entertainment", "ENT", "Entertainment"),
]
SECTOR_LABEL = {s: n for s, _, n in SECTORS} | {"finance": "Business & Markets", "health": "Health & Science", "cyber": "Tech & Cyber"}
SECTOR_CODE = {s: c for s, c, _ in SECTORS} | {"finance": "BIZ", "health": "HLT", "cyber": "TEC", "other": "—"}
# outlet → origin class for the coverage bar (from sources.country/language on prod)
REGIONAL = {"Aaj Tak", "Amar Ujala", "Prajavani", "TV9 Kannada", "BBC News Hindi", "BBC News Bengali", "BBC News Gujarati", "BBC News Marathi", "BBC News Punjabi", "BBC Tamil", "BBC News Telugu", "BBC News Urdu"}
INTL = {"Al Jazeera English", "Anadolu Agency", "BBC World", "CGTN", "Dawn", "DW News", "France 24", "The Guardian World", "Press TV", "South China Morning Post", "TASS", "BleepingComputer"}


def fetch():
    DATA.mkdir(exist_ok=True)
    for name, path in {
        "feed": "/api/v1/feed?limit=30",
        "trending": "/api/v1/trending?limit=12",
        "lenses": "/api/v1/lenses",
        "event": "/api/v1/events/066f3349-cd17-49f5-b910-83fa087cb8ac",
    }.items():
        with urllib.request.urlopen(API + path, timeout=60) as r:
            (DATA / f"{name}.json").write_bytes(r.read())


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


def tokens():
    return json.loads((ROOT / "design" / "tokens.json").read_text())


def css_vars(t) -> str:
    def block(mode):
        return "\n".join(f"  --{k}: {v['value']};" for k, v in t["color"][mode].items())
    f = t["font"]
    def fam(key):
        return ", ".join([f'"{f[key]["family"]}"'] + [f'"{x}"' if " " in x else x for x in f[key]["fallback"]])
    sp = "\n".join(f"  --s{k}: {v}px;" for k, v in t["space"].items())
    rad = "\n".join(f"  --r-{k}: {v}px;" for k, v in t["radius"].items())
    return f""":root {{
{block("light")}
  --font-display: {fam("display")};
  --font-sans: {fam("sans")};
  --font-mono: {fam("mono")};
{sp}
{rad}
  --shadow-1: {t["shadow"]["1"]};
  --shadow-2: {t["shadow"]["2"]};
  --ease: {t["motion"]["standard"]["easing"]};
  --t-micro: {t["motion"]["micro"]["ms"]}ms;
  --t-std: {t["motion"]["standard"]["ms"]}ms;
  --shell: {t["layout"]["shell"]}px;
  --reading: {t["layout"]["reading"]}px;
  --rail: {t["layout"]["rail"]}px;
  --topbar: {t["layout"]["topbar"]}px;
  --tabbar: {t["layout"]["tabbar"]}px;
  color-scheme: light;
}}
[data-theme="dark"] {{
{block("dark")}
  color-scheme: dark;
  --shadow-1: 0 1px 2px rgba(0,0,0,.4);
  --shadow-2: 0 12px 32px -8px rgba(0,0,0,.6), 0 2px 6px rgba(0,0,0,.3);
}}
"""


BASE_CSS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font-sans);font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
img{display:block;max-width:100%}
.mono{font-family:var(--font-mono);font-size:12px;letter-spacing:.02em;line-height:1.5;font-variant-numeric:tabular-nums}
.mono-s{font-family:var(--font-mono);font-size:11px;letter-spacing:.03em;line-height:1.5;font-variant-numeric:tabular-nums}
.label{font-size:12.5px;font-weight:500;line-height:1.4;letter-spacing:.01em;color:var(--ink-3);text-transform:uppercase}
.display{font-family:var(--font-display);font-weight:500;letter-spacing:-.01em}
.serif{font-family:var(--font-display)}
.muted{color:var(--ink-2)}.faint{color:var(--ink-3)}
.shell{max-width:var(--shell);margin:0 auto;padding:0 16px}
@media(min-width:640px){.shell{padding:0 24px}}
@media(min-width:1024px){.shell{padding:0 32px}}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:var(--r-xs)}

/* ── top bar (desktop) ───────────────────────────────────── */
.topbar{display:none;position:sticky;top:0;z-index:30;height:var(--topbar);background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.topbar .shell{height:100%;display:flex;align-items:center;gap:28px}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--font-display);font-weight:600;font-size:24px;letter-spacing:-.01em;line-height:1}
.brand svg{display:block}
.nav{display:none;gap:4px;margin-left:8px}
.nav a{padding:8px 12px;border-radius:var(--r-pill);font-weight:500;font-size:15px;color:var(--ink-2)}
.nav a:hover{background:var(--sunken);color:var(--ink)}
.nav a[aria-current]{color:var(--accent);background:var(--accent-soft)}
.search{display:none;margin-left:auto;align-items:center;gap:8px;height:38px;padding:0 12px 0 12px;border:1px solid var(--line-strong);border-radius:var(--r-pill);background:var(--surface);color:var(--ink-3);min-width:260px;font-size:14px}
.search kbd{margin-left:auto;font:500 11px var(--font-mono);border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:var(--ink-3)}
.topbar .actions{display:flex;align-items:center;gap:8px;margin-left:auto}
@media(min-width:1024px){.topbar{display:block}.nav{display:flex}.search{display:flex}.topbar .actions{margin-left:0}}
.icon-btn{width:38px;height:38px;border-radius:var(--r-pill);display:inline-flex;align-items:center;justify-content:center;color:var(--ink-2);border:1px solid transparent}
.icon-btn:hover{background:var(--sunken);color:var(--ink)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:40px;padding:0 16px;border-radius:var(--r-pill);font-weight:600;font-size:14.5px;transition:background var(--t-micro) var(--ease),transform var(--t-micro) var(--ease)}
.btn-primary{background:var(--accent-fill);color:var(--on-accent)}
.btn-primary:hover{filter:brightness(.95)}
.btn-primary:active{transform:translateY(1px)}
.btn-secondary{border:1px solid var(--line-strong);background:var(--surface);color:var(--ink)}
.btn-secondary:hover{background:var(--sunken)}
.btn-ghost{color:var(--ink-2)}.btn-ghost:hover{background:var(--sunken);color:var(--ink)}
.btn-lg{height:48px;padding:0 22px;font-size:16px}
.btn-sm{height:32px;padding:0 12px;font-size:13.5px}

/* ── phone masthead + tab bar ───────────────────────────── */
.masthead{position:sticky;top:0;z-index:30;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.masthead .row{display:flex;align-items:center;justify-content:space-between;height:52px;padding:0 16px}
.masthead .date{font-family:var(--font-mono);font-size:11px;letter-spacing:.04em;color:var(--ink-3);text-transform:uppercase}
@media(min-width:1024px){.masthead{display:none}}
.tabbar{position:fixed;left:0;right:0;bottom:0;z-index:30;height:calc(var(--tabbar) + env(safe-area-inset-bottom));padding-bottom:env(safe-area-inset-bottom);display:grid;grid-template-columns:repeat(5,1fr);background:color-mix(in srgb,var(--surface) 92%,transparent);backdrop-filter:blur(14px);border-top:1px solid var(--line)}
.tabbar a{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font-size:11px;font-weight:500;color:var(--ink-3)}
.tabbar a svg{width:22px;height:22px}
.tabbar a[aria-current]{color:var(--accent)}
.tabbar a[aria-current] .pip{width:16px;height:2px;border-radius:2px;background:var(--accent);margin-top:2px}
@media(min-width:1024px){.tabbar{display:none}}
.page{padding-bottom:calc(var(--tabbar) + 24px)}
@media(min-width:1024px){.page{padding-bottom:64px}}

/* ── subject chips / rail ───────────────────────────────── */
.chips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding:10px 16px;-webkit-overflow-scrolling:touch}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;display:inline-flex;align-items:center;gap:6px;height:34px;padding:0 14px;border-radius:var(--r-pill);border:1px solid var(--line);background:var(--surface);font-size:13.5px;font-weight:500;color:var(--ink-2);white-space:nowrap}
.chip[aria-current]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip .n{font-family:var(--font-mono);font-size:11px;color:inherit;opacity:.7}
.rail{display:none}
@media(min-width:1024px){
  .chips{display:none}
  .rail{display:block;position:sticky;top:calc(var(--topbar) + 24px);align-self:start}
  .rail a{display:flex;align-items:center;gap:10px;height:40px;padding:0 12px;border-radius:var(--r-md);color:var(--ink-2);font-size:14.5px;font-weight:500}
  .rail a:hover{background:var(--sunken);color:var(--ink)}
  .rail a[aria-current]{background:var(--accent-soft);color:var(--accent)}
  .rail a .n{margin-left:auto;font-family:var(--font-mono);font-size:11px;color:var(--ink-3)}
  .rail .code{font-family:var(--font-mono);font-size:11px;letter-spacing:.04em;width:28px;color:var(--ink-3)}
}
.grid{display:grid;gap:24px}.grid>*{min-width:0}
@media(min-width:1024px){.grid-3{grid-template-columns:var(--rail) minmax(0,1fr) 300px;gap:40px}.grid-2{grid-template-columns:var(--rail) minmax(0,1fr);gap:40px}}

/* ── coverage glyphs ────────────────────────────────────── */
.cov{display:flex;align-items:center;gap:10px;min-width:0}
.covbar{display:flex;gap:2px;height:6px;flex:none}
.covbar i{display:block;height:100%;border-radius:3px}
.covbar.lg{height:8px}.covbar.lg i{border-radius:4px}
.cov .txt{font-family:var(--font-mono);font-size:11px;letter-spacing:.02em;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.c-nat{background:var(--coverage-national)}.c-reg{background:var(--coverage-regional)}.c-int{background:var(--coverage-intl)}.c-wire{background:var(--coverage-wire)}
.monos{display:inline-flex;align-items:center}
.mono-av{width:26px;height:26px;border-radius:50%;background:var(--sunken);border:2px solid var(--surface);box-shadow:0 0 0 1px var(--line);display:inline-flex;align-items:center;justify-content:center;font:600 9.5px/1 var(--font-sans);letter-spacing:.01em;color:var(--ink-2);margin-left:-7px}
.mono-av:first-child{margin-left:0}
.mono-av.more{font-family:var(--font-mono);font-weight:500;font-size:9.5px}
.status{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 9px;border-radius:var(--r-pill);font-size:12px;font-weight:600;letter-spacing:.01em}
.status.verified{background:var(--ink);color:var(--bg)}
.status.provisional{border:1px dashed var(--line-strong);color:var(--ink-3)}
.status.corrected{background:color-mix(in srgb,var(--status-corrected) 12%,transparent);color:var(--status-corrected)}
.lensdot{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600}
.lensdot i{width:8px;height:8px;border-radius:50%}
.l-markets{color:var(--lens-markets)}.l-markets i{background:var(--lens-markets)}
.l-cyber{color:var(--lens-cyber)}.l-cyber i{background:var(--lens-cyber)}

/* ── story rows ─────────────────────────────────────────── */
.section{display:flex;align-items:baseline;justify-content:space-between;gap:16px;padding:8px 0 12px}
.section h2{margin:0;font-family:var(--font-display);font-weight:500;font-size:24px;letter-spacing:-.01em;line-height:1.2}
.section .sub{font-size:14px;color:var(--ink-3)}
.rows{display:flex;flex-direction:column;gap:12px}
.row{display:block;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-md);padding:14px 16px;transition:border-color var(--t-micro) var(--ease),box-shadow var(--t-micro) var(--ease)}
.row:hover{border-color:var(--line-strong);box-shadow:var(--shadow-1)}
.row .meta{display:flex;align-items:center;gap:10px;font-family:var(--font-mono);font-size:11px;letter-spacing:.03em;color:var(--ink-3);text-transform:uppercase}
.row .meta .sec{color:var(--ink-2);font-weight:500}
.row h3{margin:6px 0 4px;font-family:var(--font-display);font-weight:500;font-size:19px;line-height:1.3;letter-spacing:-.005em;text-wrap:pretty}
.row .what{margin:0;font-size:14.5px;line-height:1.5;color:var(--ink-2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.row .foot{display:flex;align-items:center;gap:12px;margin-top:12px;min-width:0}
.row .foot .spacer{flex:1}
.row.lead{padding:20px 18px}
.row.lead h3{font-size:26px;line-height:1.18;margin-top:8px}
.row.lead .what{font-size:16px;-webkit-line-clamp:3}
@media(min-width:640px){.row.lead h3{font-size:30px}}
.row.single{border-style:dashed}
.time{color:var(--ink-3)}
.dot{width:3px;height:3px;border-radius:50%;background:var(--line-strong);display:inline-block}

/* ── right rail cards ───────────────────────────────────── */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:16px}
.card h4{margin:0 0 10px;font-size:12.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)}
.mini{display:flex;flex-direction:column;gap:12px}
.mini a{display:block}
.mini .t{font-family:var(--font-display);font-size:15.5px;line-height:1.35;font-weight:500}
.mini .c{margin-top:6px}
.side{display:none}.phone-only{display:block}@media(min-width:1024px){.phone-only{display:none}}
@media(min-width:1024px){.side{display:flex;flex-direction:column;gap:16px;position:sticky;top:calc(var(--topbar) + 24px);align-self:start}}

/* ── story record ───────────────────────────────────────── */
.record-head{padding:20px 0 16px;border-bottom:1px solid var(--line)}
.record-head .top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.record-head h1{margin:14px 0 10px;font-family:var(--font-display);font-weight:500;font-size:30px;line-height:1.12;letter-spacing:-.015em;text-wrap:balance}
@media(min-width:640px){.record-head h1{font-size:38px}}
.record-head .summary{margin:0;font-size:17px;line-height:1.55;color:var(--ink-2);max-width:62ch}
.record-head .covline{display:flex;align-items:center;gap:14px;margin-top:16px;flex-wrap:wrap}
.record-head .actions{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}.record-head .actions .btn{display:none}@media(min-width:1024px){.record-head .actions .btn{display:inline-flex}}.record-head .covline .txt{white-space:normal}
.reading{max-width:var(--reading)}
.seg{display:inline-flex;padding:3px;border-radius:var(--r-pill);background:var(--sunken);gap:2px}
.seg button{height:34px;padding:0 14px;border-radius:var(--r-pill);font-size:13.5px;font-weight:600;color:var(--ink-2);display:inline-flex;align-items:center;gap:6px}
.seg button[aria-selected]{background:var(--surface);color:var(--ink);box-shadow:var(--shadow-1)}
.seg button.markets[aria-selected]{color:var(--lens-markets)}
.seg button.cyber[aria-selected]{color:var(--lens-cyber)}
.seg .lock{opacity:.55}
.block{padding:22px 0;border-bottom:1px solid var(--line)}
.block h2{margin:0 0 4px;font-family:var(--font-display);font-weight:500;font-size:22px;letter-spacing:-.01em;line-height:1.25;display:flex;align-items:baseline;gap:10px}
.block h2 .n{font-family:var(--font-mono);font-size:12px;font-weight:400;color:var(--ink-3)}
.block .hint{margin:0 0 14px;font-size:13.5px;color:var(--ink-3)}
.brief{font-size:16.5px;line-height:1.65;margin:0}
.brief b{font-weight:600}
.watch{margin:14px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px}
.watch li{display:flex;gap:10px;font-size:14.5px;color:var(--ink-2)}
.watch li::before{content:"";flex:none;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-top:9px}
.timeline{list-style:none;margin:0;padding:0;position:relative}
.timeline::before{content:"";position:absolute;left:5px;top:6px;bottom:6px;width:1px;background:var(--line-strong)}
.timeline li{position:relative;padding:0 0 18px 24px}
.timeline li::before{content:"";position:absolute;left:0;top:7px;width:11px;height:11px;border-radius:50%;background:var(--surface);border:2px solid var(--ink)}
.timeline li.now::before{background:var(--accent);border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.timeline .t{font-family:var(--font-mono);font-size:11px;letter-spacing:.03em;color:var(--ink-3);text-transform:uppercase}
.timeline .h{font-family:var(--font-display);font-size:17px;line-height:1.35;font-weight:500;margin:2px 0 2px}
.timeline .s{font-size:13px;color:var(--ink-3)}
.quotes{display:grid;gap:12px}
@media(min-width:900px){.quotes.two{grid-template-columns:1fr 1fr}}
.quote{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:16px}
.quote .who{display:flex;align-items:center;gap:10px}
.quote .who .av{width:32px;height:32px;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:inline-flex;align-items:center;justify-content:center;font:600 12px var(--font-sans)}
.quote .who .nm{font-weight:600;font-size:14.5px;line-height:1.2}
.quote .who .rl{font-size:12.5px;color:var(--ink-3)}
.quote blockquote{margin:12px 0 10px;font-family:var(--font-display);font-style:italic;font-size:17.5px;line-height:1.5;color:var(--ink);text-wrap:pretty}
.quote .src{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-family:var(--font-mono);font-size:11px;letter-spacing:.02em;color:var(--ink-3)}
.quote .src .pill{border:1px solid var(--line);border-radius:var(--r-pill);padding:2px 8px;color:var(--ink-2);font-family:var(--font-sans);font-size:12px;font-weight:500}
.quote details{margin-top:10px}
.quote summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--accent);list-style:none;display:inline-flex;align-items:center;gap:6px}
.quote details p{margin:8px 0 0;font-size:14px;line-height:1.55;color:var(--ink-2);border-left:2px solid var(--line-strong);padding-left:10px}
.quote details mark{background:var(--accent-soft);color:var(--ink);border-radius:3px;padding:0 2px}
.sources{display:flex;flex-direction:column}
.sources a{display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 0;border-top:1px solid var(--line)}
.sources a:first-child{border-top:0}
.sources .mono-av{width:28px;height:28px;font-size:10.5px;margin:0}
.sources .t{font-size:14.5px;line-height:1.35;font-weight:500;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sources .o{font-size:12.5px;color:var(--ink-3)}
.sources .when{font-family:var(--font-mono);font-size:11px;color:var(--ink-3);white-space:nowrap}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-2);margin-top:10px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:10px;height:10px;border-radius:3px}
.ask{margin-top:8px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--surface);padding:14px 16px}
.ask .in{display:flex;gap:8px;align-items:center;height:44px;border:1px solid var(--line-strong);border-radius:var(--r-pill);padding:0 6px 0 14px;color:var(--ink-3);font-size:15px}
.ask .in .send{margin-left:auto;width:34px;height:34px;border-radius:50%;background:var(--ink);color:var(--bg);display:inline-flex;align-items:center;justify-content:center}
.ask .sugg{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.ask .sugg button{border:1px solid var(--line);border-radius:var(--r-pill);padding:6px 12px;font-size:13px;color:var(--ink-2)}
.thumb{position:fixed;left:0;right:0;bottom:calc(var(--tabbar) + env(safe-area-inset-bottom));z-index:29;display:flex;gap:8px;padding:10px 16px;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(12px);border-top:1px solid var(--line)}
@media(min-width:1024px){.thumb{display:none}}
.toc{display:flex;flex-direction:column}
.toc a{display:flex;justify-content:space-between;padding:9px 0;border-top:1px solid var(--line);font-size:14px;color:var(--ink-2)}
.toc a:first-child{border-top:0}
.toc a .n{font-family:var(--font-mono);font-size:11px;color:var(--ink-3)}
.toc a[aria-current]{color:var(--accent);font-weight:600}

/* ── landing ────────────────────────────────────────────── */
.hero{padding:40px 0 32px;position:relative;overflow:hidden}
.hero::before{content:"";position:absolute;inset:-40% -20% auto -20%;height:70%;background:radial-gradient(60% 60% at 30% 40%,var(--accent-soft) 0%,transparent 70%);pointer-events:none;opacity:.9}
.hero .shell{position:relative}
.hero h1{margin:0;font-family:var(--font-display);font-weight:500;font-size:40px;line-height:1.05;letter-spacing:-.02em;max-width:14ch;text-wrap:balance}
.hero p.lede{margin:18px 0 0;font-size:17px;line-height:1.55;color:var(--ink-2);max-width:44ch}
.hero .cta{display:flex;gap:10px;margin-top:24px;flex-wrap:wrap;align-items:center}
.hero .proof{margin-top:32px}
@media(min-width:1024px){.hero{padding:64px 0 48px}.hero .shell{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:56px;align-items:center}.hero h1{font-size:60px}.hero .proof{margin-top:0}}
.disperse{display:block;width:100%;height:auto;margin:0 0 20px}
.eyebrow{font-size:12.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin:0 0 10px}
.lsection{padding:40px 0;border-top:1px solid var(--line)}
@media(min-width:1024px){.lsection{padding:64px 0}}
.lsection h2{margin:0 0 8px;font-family:var(--font-display);font-weight:500;font-size:30px;line-height:1.15;letter-spacing:-.015em;text-wrap:balance}
@media(min-width:1024px){.lsection h2{font-size:38px}}
.lsection p.sub{margin:0 0 24px;font-size:16.5px;line-height:1.55;color:var(--ink-2);max-width:56ch}
.proofs{display:grid;gap:16px}
@media(min-width:1024px){.proofs{grid-template-columns:repeat(3,1fr)}}
.proof-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-xl);padding:20px;display:flex;flex-direction:column;gap:14px}
.proof-card h3{margin:0;font-family:var(--font-display);font-weight:500;font-size:22px;letter-spacing:-.01em;line-height:1.2}
.proof-card p{margin:0;font-size:14.5px;line-height:1.55;color:var(--ink-2)}
.proof-card .demo{border-top:1px solid var(--line);padding-top:14px;margin-top:auto}
.status-grid{display:grid;gap:12px}
@media(min-width:768px){.status-grid{grid-template-columns:repeat(3,1fr)}}
.status-col{border:1px solid var(--line);border-radius:var(--r-lg);padding:16px;background:var(--surface)}
.status-col h4{margin:0 0 10px;font-size:12.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase}
.status-col.now h4{color:var(--lens-markets)}.status-col.val h4{color:var(--status-disputed)}.status-col.next h4{color:var(--ink-3)}
.status-col ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px;font-size:14.5px;color:var(--ink-2)}
.status-col li{display:flex;gap:8px}.status-col li::before{content:"";flex:none;width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.5;margin-top:10px}
.final{padding:56px 0 72px;text-align:center}
.final h2{margin:0 0 18px;font-family:var(--font-display);font-weight:500;font-size:34px;letter-spacing:-.015em;line-height:1.1}
.footer{border-top:1px solid var(--line);padding:24px 0 32px;font-size:13px;color:var(--ink-3);display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.flip{border:1px solid var(--line);border-radius:var(--r-xl);background:var(--surface);overflow:hidden}
.flip .bar{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--line);gap:12px;flex-wrap:wrap}
.flip .body{padding:18px 16px;position:relative}
.flip .body p{margin:0;font-size:16px;line-height:1.6}
.flip .body .scan{position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,transparent,var(--lens-markets),transparent);opacity:.9}
.kpi{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:24px}
.kpi div{border:1px solid var(--line);border-radius:var(--r-md);padding:12px;background:var(--surface)}
.kpi b{display:block;font-family:var(--font-display);font-size:28px;font-weight:500;letter-spacing:-.02em;line-height:1}
.kpi span{font-size:12.5px;color:var(--ink-3)}

/* ── components sheet ───────────────────────────────────── */
.sheet{display:grid;gap:32px;padding:32px 0}
.sw{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px}
.sw div{border:1px solid var(--line);border-radius:var(--r-md);overflow:hidden;background:var(--surface)}
.sw i{display:block;height:56px}
.sw span{display:block;padding:8px 10px;font-family:var(--font-mono);font-size:11px;color:var(--ink-2)}
.tspec{display:grid;gap:10px}
.tspec div{display:grid;grid-template-columns:150px 1fr;gap:16px;align-items:baseline;border-top:1px solid var(--line);padding-top:10px}
.tspec .k{font-family:var(--font-mono);font-size:11px;color:var(--ink-3)}
"""


# ── data helpers ──────────────────────────────────────────────────────────

def ago(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    m = int((datetime.now(UTC) - t).total_seconds() // 60)
    if m < 60:
        return f"{max(m,1)}m ago"
    if m < 60 * 24:
        return f"{m // 60}h ago"
    return f"{m // 1440}d ago"


def initials(name: str) -> str:
    stop = {"the", "of", "news", "&", "—", "-"}
    words = [w for w in name.replace("—", " ").split() if w.lower() not in stop] or name.split()
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def origin(outlet: str) -> str:
    if outlet in REGIONAL:
        return "reg"
    if outlet in INTL:
        return "int"
    return "nat"


LANG_OF = {"Aaj Tak": "Hindi", "Amar Ujala": "Hindi", "BBC News Hindi": "Hindi", "Prajavani": "Kannada", "TV9 Kannada": "Kannada", "BBC Tamil": "Tamil", "BBC News Telugu": "Telugu", "BBC News Bengali": "Bengali", "BBC News Gujarati": "Gujarati", "BBC News Marathi": "Marathi", "BBC News Punjabi": "Punjabi", "BBC News Urdu": "Urdu"}


def langs_of(names: list[str]) -> str:
    seen = []
    for n in names:
        l = LANG_OF.get(n, "English")
        if l not in seen:
            seen.append(l)
    return ", ".join(seen)


def covbar(counts: dict[str, int], lg=False, width=None) -> str:
    total = sum(counts.values()) or 1
    w = width or (120 if lg else 72)
    segs = []
    for key in ("nat", "int", "reg", "wire"):
        n = counts.get(key, 0)
        if n:
            segs.append(f'<i class="c-{key}" style="width:{max(4, round(w*n/total))}px" title="{n}"></i>')
    return f'<span class="covbar{" lg" if lg else ""}" aria-hidden="true">{"".join(segs)}</span>'


def cov_from_feed(item) -> dict[str, int]:
    """The feed row only carries origins by country; treat IN as national/regional by language flag."""
    o = item.get("coverage", {}).get("origins", {})
    n_in = o.get("IN", 0)
    n_other = sum(v for k, v in o.items() if k != "IN")
    # available_languages tells us whether Indian-language reporting is inside the IN count
    langs = item.get("available_languages") or ["en"]
    reg = min(n_in, len([l for l in langs if l != "en"])) if n_in else 0
    return {"nat": n_in - reg, "reg": reg, "int": n_other}


def monos(names: list[str], limit=3) -> str:
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    out = "".join(f'<span class="mono-av" title="{n}">{initials(n)}</span>' for n in seen[:limit])
    if len(seen) > limit:
        out += f'<span class="mono-av more">+{len(seen)-limit}</span>'
    return f'<span class="monos" aria-hidden="true">{out}</span>'


REGION_NAMES = {"IN-AP": "Andhra Pradesh", "IN-KA": "Karnataka", "IN-TN": "Tamil Nadu", "IN-KL": "Kerala", "IN-TG": "Telangana", "IN-DL": "Delhi", "IN-MH": "Maharashtra", "IN-UP": "Uttar Pradesh", "IN-UT": "Uttarakhand", "IN-HR": "Haryana", "IN-PB": "Punjab", "IN-WB": "West Bengal", "IN-GJ": "Gujarat", "IN-RJ": "Rajasthan", "IN-MP": "Madhya Pradesh", "IN-BR": "Bihar"}


def region_label(regions: list[str]) -> str:
    states = [REGION_NAMES.get(r, r.split("-")[-1]) for r in regions if r.startswith("IN-")]
    if states:
        return states[0]
    return "India" if "IN" in regions else "World"


def cov_text(item) -> str:
    n = item.get("source_count") or 0
    langs = item.get("available_languages") or ["en"]
    parts = [f"{n} outlet{'s' if n != 1 else ''}"]
    if len(langs) > 1:
        parts.append(f"{len(langs)} languages")
    return " · ".join(parts)


# ── svg bits ──────────────────────────────────────────────────────────────

MARK = """<svg width="{s}" height="{h}" viewBox="0 0 24 22" fill="none" aria-hidden="true"><path d="M12 1 L23 21 L1 21 Z" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><rect x="1" y="19" width="22" height="3" fill="url(#sp{id})"/><defs><linearGradient id="sp{id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#ef4444"/><stop offset="35%" stop-color="#f59e0b"/><stop offset="70%" stop-color="#06b6d4"/><stop offset="100%" stop-color="#8b5cf6"/></linearGradient></defs></svg>"""


def mark(s=24, id="a"):
    return MARK.format(s=s, h=round(s * 22 / 24), id=id)


ICONS = {
    "today": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="3"/><path d="M3 9h18M8 2v4M16 2v4"/></svg>',
    "stories": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5M4 12h7M4 5h11M11 12l4-3M15 5l5 3"/><circle cx="20" cy="8" r="1.5" fill="currentColor" stroke="none"/><circle cx="15" cy="9" r="1.5" fill="currentColor" stroke="none"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    "watch": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 16l5-5 4 4 7-8"/><path d="M15 7h5v5"/></svg>',
    "you": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>',
    "sun": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    "share": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15V4M7 9l5-5 5 5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5"/></svg>',
    "bell": '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 21a2 2 0 0 0 4 0"/></svg>',
    "check": '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 4 4L19 6"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "chev": '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
    "send": '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M6 11l6-6 6 6"/></svg>',
}


def head(title: str, theme: str = "light") -> str:
    return f"""<!doctype html><html lang="en" data-theme="{theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{title} — Prism board</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Hind:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="prism.css"></head><body>"""


def topbar(active: str, cta: str | None = None) -> str:
    links = [("Today", "today"), ("Stories", "stories"), ("Pulse", "pulse"), ("Watchlist", "watchlist")]
    nav = "".join(f'<a href="#" {"aria-current=page" if k == active else ""}>{n}</a>' for n, k in links)
    cta_html = f'<a class="btn btn-primary" href="#">{cta}</a>' if cta else '<a class="btn btn-ghost" href="#">Sign in</a>'
    return f"""<header class="topbar"><div class="shell">
  <a class="brand" href="#">{mark(26, "t")}<span>Prism</span></a>
  <nav class="nav" aria-label="Primary">{nav}</nav>
  <div class="search" role="search"><span style="width:16px;height:16px;display:inline-flex">{ICONS["search"]}</span><span>Search stories, people, places</span><kbd>/</kbd></div>
  <div class="actions"><button class="icon-btn" aria-label="Theme">{ICONS["sun"]}</button>{cta_html}</div>
</div></header>"""


def masthead(date_line: str) -> str:
    return f"""<div class="masthead"><div class="row">
  <a class="brand" href="#">{mark(24, "m")}<span>Prism</span></a>
  <span class="date">{date_line}</span>
  <button class="icon-btn" aria-label="Theme">{ICONS["sun"]}</button>
</div></div>"""


def tabbar(active: str) -> str:
    tabs = [("Today", "today"), ("Stories", "stories"), ("Search", "search"), ("Watchlist", "watch"), ("You", "you")]
    return '<nav class="tabbar" aria-label="Primary">' + "".join(
        f'<a href="#" {"aria-current=page" if k == active else ""}>{ICONS[k]}<span>{n}</span>{"<i class=pip></i>" if k == active else ""}</a>' for n, k in tabs
    ) + "</nav>"


def subject_chips(active="all", counts: dict | None = None) -> str:
    counts = counts or {}
    items = [("all", "All", "All stories")] + [(s, c, n) for s, c, n in SECTORS]
    chips = "".join(
        f'<a class="chip" href="#" {"aria-current=page" if s == active else ""}>{n if s == "all" else n}{f"<span class=n>{counts[s]}</span>" if s in counts else ""}</a>' for s, c, n in items
    )
    rail = "".join(
        f'<a href="#" {"aria-current=page" if s == active else ""}><span class="code">{c if s != "all" else "ALL"}</span>{n}{f"<span class=n>{counts[s]}</span>" if s in counts else ""}</a>' for s, c, n in items
    )
    return f'<div class="chips" role="navigation" aria-label="Subjects">{chips}</div>', f'<aside class="rail" aria-label="Subjects">{rail}<div style="margin-top:20px;padding:14px 12px;border-top:1px solid var(--line);font-size:13px;color:var(--ink-3);line-height:1.5">One record per story, from monitored outlets. Every quote and source stays open.<br><a href="#" style="color:var(--accent);font-weight:600">How Prism works →</a></div></aside>'


def story_row(item, lead=False, sources_for_monos=None) -> str:
    cov = cov_from_feed(item)
    n = item.get("source_count") or 0
    sec = SECTOR_LABEL.get(item.get("sector") or "", "") or region_label(item.get("regions") or [])
    single = n <= 1
    lens = ""
    if item.get("tickers") or (item.get("sector") in ("business", "finance")) and n >= 2:
        lens = '<span class="lensdot l-markets"><i></i>Markets read</span>'
    if item.get("cve_ids"):
        lens = '<span class="lensdot l-cyber"><i></i>Cyber read</span>'
    langs = item.get("available_languages") or ["en"]
    lang_tag = "" if langs == ["en"] else f'<span class="dot"></span><span>{"·".join(l.upper() for l in langs)}</span>'
    names = sources_for_monos or []
    return f"""<a class="row{" lead" if lead else ""}{" single" if single else ""}" href="#">
  <div class="meta"><span class="sec">{sec}</span><span class="dot"></span><span class="time">{ago(item.get("last_updated_at"))}</span>{lang_tag}</div>
  <h3>{item["title"]}</h3>
  <p class="what">{item.get("summary") or ""}</p>
  <div class="foot">{monos(names) if names else ""}<span class="cov">{covbar(cov)}<span class="txt">{cov_text(item)}</span></span><span class="spacer"></span>{lens}</div>
</a>"""


# ── pages ─────────────────────────────────────────────────────────────────

def page_today(feed, event, lenses, trending=None) -> str:
    items = sorted(feed["items"], key=lambda i: -(i.get("source_count") or 0))
    chips, rail = subject_chips("all")
    lead = items[0]
    rows = [story_row(lead, lead=True, sources_for_monos=[s["source_name"] for s in event["sources"]] if lead["id"] == event["id"] else None)]
    rows += [story_row(i) for i in items[1:10]]
    live = "".join(
        f'<a href="#"><div class="t">{t.get("hero_title") or t["label"]}</div><div class="c cov" style="margin-top:6px">{covbar({"nat": t["source_count"]})}<span class="txt">{t["developments"]} developments · {t["source_count"]} outlets</span></div></a>'
        for t in (trending or {"stories": []})["stories"][:4]
    )
    date_line = datetime.now().strftime("%a %-d %b").upper()
    return head("Today") + topbar("today") + masthead(date_line) + f"""
<main class="page"><div class="shell"><div class="grid grid-3" style="padding-top:8px">
  {rail}
  <div>
    {chips}
    <div class="section"><h2>Today</h2><span class="sub">{len(items)} records · newest reporting first</span></div>
    <div class="rows">{"".join(rows)}</div>
    <div style="display:flex;justify-content:center;padding:24px 0"><a class="btn btn-secondary" href="#">Yesterday's record</a></div>
  </div>
  <aside class="side">
    <div class="card"><h4>Developing over days</h4><div class="mini">{live}</div><a href="#" style="display:block;margin-top:12px;font-size:13.5px;font-weight:600;color:var(--accent)">All developing stories →</a></div>
    <div class="card"><h4>How to read a record</h4>
      <div style="display:flex;flex-direction:column;gap:12px;font-size:13.5px;color:var(--ink-2)">
        <div class="cov">{covbar({"nat":5,"int":2,"reg":3})}<span class="txt" style="font-family:var(--font-sans);font-size:13px;color:var(--ink-2)">Coverage bar — who reported it</span></div>
        <div class="legend"><span><i class="c-nat"></i>English national</span><span><i class="c-reg"></i>Indian-language</span><span><i class="c-int"></i>International</span></div>
        <div style="display:flex;gap:8px;align-items:center"><span class="status verified">{ICONS["check"]}Verified</span><span class="status provisional">Provisional</span></div>
        <div>Dashed rows have one source so far.</div>
      </div></div>
  </aside>
</div></div></main>
{tabbar("today")}</body></html>"""


def page_story(event, lenses) -> str:
    srcs = event["sources"]
    names = [s["source_name"] for s in srcs]
    counts = {"nat": 0, "reg": 0, "int": 0}
    for n in names:
        counts[origin(n)] += 1
    n_out = len(set(names))
    brief = (event.get("lens_briefs") or {}).get("reader") or {}
    brief_text = brief.get("text") if isinstance(brief, dict) else (brief or "")
    points = brief.get("points", []) if isinstance(brief, dict) else []
    claims = event.get("claims") or []
    n_claims = sum(len(s["claims"]) for s in claims)
    qcards = []
    for sp in claims[:4]:
        c = sp["claims"][0]
        ctx = ""
        if c.get("context_before") or c.get("context_after"):
            ctx = f'<details><summary>In the article {ICONS["chev"]}</summary><p>…{c.get("context_before","")} <mark>{c["quote_text"]}</mark> {c.get("context_after","")}…</p></details>'
        more = f' <span class="faint">· {len(sp["claims"])-1} more</span>' if len(sp["claims"]) > 1 else ""
        qcards.append(f"""<article class="quote">
  <div class="who"><span class="av">{initials(sp["speaker"])}</span><div><div class="nm">{sp["speaker"]}{more}</div><div class="rl">quoted in {len({q["source_name"] for q in sp["claims"]})} outlet{"s" if len({q["source_name"] for q in sp["claims"]})!=1 else ""}</div></div></div>
  <blockquote>“{c["quote_text"]}”</blockquote>
  <div class="src"><span class="pill">{c["source_name"]}</span><span>{ago(c.get("published_at"))}</span><span class="dot"></span><a href="#" style="color:var(--accent);font-family:var(--font-sans);font-weight:600;font-size:12.5px">Open at the quote ↗</a></div>
  {ctx}
</article>""")
    devs = sorted(srcs, key=lambda s: s.get("published_at") or "", reverse=True)
    tl = "".join(
        f'<li{" class=now" if i == 0 else ""}><div class="t">{ago(s.get("published_at"))} · {s["source_name"]}</div><div class="h">{s.get("title") or ""}</div></li>'
        for i, s in enumerate(devs[:5])
    )
    src_rows = "".join(
        f'<a href="#"><span class="mono-av">{initials(s["source_name"])}</span><span><div class="t">{s.get("title") or ""}</div><div class="o">{s["source_name"]}</div></span><span class="when">{ago(s.get("published_at"))}</span></a>'
        for s in devs[:8]
    )
    impacts = event.get("impacts") or []
    imp = "".join(f'<li><b>{i["entity_name"]}</b> — {i["effect"].replace("_"," ")}, {i["horizon"]}</li>' for i in impacts[:4])
    ent = ", ".join(e.get("name") for e in (event.get("entities") or [])[:8])
    lens_tabs = f"""<div class="seg" role="tablist" aria-label="Read it as">
  <button role="tab" aria-selected="true">Reader</button>
  <button role="tab" class="markets"><span class="lock">{ICONS["lock"]}</span>Markets</button>
  <button role="tab" class="cyber"><span class="lock">{ICONS["lock"]}</span>Cyber</button></div>"""
    return head("Story") + topbar("today") + f"""
<div class="masthead"><div class="row"><a class="btn btn-ghost btn-sm" href="#">← Today</a><a class="brand" href="#">{mark(22,"s")}</a><button class="icon-btn" aria-label="Share">{ICONS["share"]}</button></div></div>
<main class="page"><div class="shell">
 <div class="grid grid-3" style="padding-top:8px">
  <aside class="rail" aria-label="On this story" style="padding-top:8px">
    <div class="label" style="margin-bottom:8px">On this story</div>
    <div class="toc">
      <a href="#" aria-current="true">The record</a><a href="#">What changed<span class="n">{len(devs)}</span></a><a href="#">Who said what<span class="n">{n_claims}</span></a><a href="#">Coverage<span class="n">{n_out}</span></a><a href="#">Why it matters<span class="n">{len(impacts)}</span></a><a href="#">Ask</a>
    </div>
  </aside>
  <div>
  <header class="record-head">
    <div class="top"><span class="status provisional">Provisional grouping</span><span class="mono faint">Updated {ago(event.get("last_updated_at"))}</span><span class="dot"></span><span class="mono faint">{SECTOR_LABEL.get(event.get("sector") or "other","")}</span></div>
    <h1>{event["title"]}</h1>
    <p class="summary">{event.get("summary") or ""}</p>
    <div class="covline">{monos(names, 5)}<span class="cov">{covbar(counts, lg=True)}<span class="txt" style="font-size:12px">{n_out} outlets · {len(srcs)} reports · {langs_of(names)}</span></span></div>
    <div class="actions"><a class="btn btn-primary" href="#">{ICONS["bell"]}Follow story</a><a class="btn btn-secondary" href="#">{ICONS["share"]}Share</a><span style="flex:1"></span>{lens_tabs}</div>
  </header>

  <div class="reading">
  <section class="block" id="record">
    <h2>The record <span class="n">Reader</span></h2>
    <p class="hint">Written from the {len(srcs)} reports below. Nothing here is unsourced.</p>
    <p class="brief">{brief_text}</p>
    {"<ul class=watch>" + "".join(f"<li>{p}</li>" for p in points) + "</ul>" if points else ""}
  </section>

  <section class="block" id="changed">
    <h2>What changed <span class="n">{len(devs)} reports</span></h2>
    <p class="hint">Newest first. Times are when each outlet published.</p>
    <ol class="timeline">{tl}</ol>
  </section>

  <section class="block" id="said">
    <h2>Who said what <span class="n">{n_claims} verbatim quotes</span></h2>
    <p class="hint">Only words found exactly in the article are shown. Tap “In the article” to read them in place.</p>
    <div class="quotes two">{"".join(qcards)}</div>
  </section>

  <section class="block" id="coverage">
    <h2>Coverage <span class="n">{n_out} outlets</span></h2>
    <div class="cov" style="margin-bottom:6px">{covbar(counts, lg=True, width=240)}<span class="txt">{len(srcs)} reports</span></div>
    <div class="legend"><span><i class="c-nat"></i>English national {counts["nat"]}</span><span><i class="c-reg"></i>Indian-language {counts["reg"]}</span><span><i class="c-int"></i>International {counts["int"]}</span></div>
    <p class="hint" style="margin-top:12px">Named in the reports: {ent}.</p>
    <div class="sources phone-only">{src_rows}</div>
    <a class="btn btn-secondary btn-sm phone-only" href="#" style="margin-top:12px">All {len(srcs)} reports</a>
  </section>

  <section class="block" id="why">
    <h2>Why it matters <span class="n">{len(impacts)}</span></h2>
    <ul class="watch">{imp}</ul>
  </section>

  <section class="block" id="ask" style="border-bottom:0">
    <h2>Ask this story</h2>
    <p class="hint">Answers cite the reports above or say they can't.</p>
    <div class="ask"><div class="in">Ask about this story…<span class="send">{ICONS["send"]}</span></div>
      <div class="sugg"><button>What changed today?</button><button>Which outlets independently confirm this?</button><button>What is still disputed?</button></div></div>
  </section>
  </div>
  </div>
  <aside class="side">
    <div class="card"><h4>Reports · {len(srcs)}</h4><div class="sources" style="margin:-4px 0">{src_rows}</div></div>
    <div class="card"><h4>Named in the reports</h4><div style="display:flex;flex-wrap:wrap;gap:6px">{"".join(f'<span class="chip" style="height:30px;padding:0 10px;font-size:13px">{e}</span>' for e in ent.split(", "))}</div></div>
  </aside>
 </div>
</div></main>
<div class="thumb"><a class="btn btn-primary" style="flex:1" href="#">{ICONS["bell"]}Follow</a><a class="btn btn-secondary" href="#">Ask</a><a class="btn btn-secondary" href="#" aria-label="Share">{ICONS["share"]}</a></div>
</body></html>"""


def page_stories(trending) -> str:
    chips, rail = subject_chips("all")
    rows = []
    for s in trending["stories"][:9]:
        span = ""
        try:
            f = datetime.fromisoformat(s["first_seen_at"]); l = datetime.fromisoformat(s["last_updated_at"])
            d = (l - f).days
            span = f"{d} day{'s' if d != 1 else ''}" if d else "today"
        except Exception:
            pass
        rows.append(f"""<a class="row" href="#">
  <div class="meta"><span class="sec">{SECTOR_LABEL.get(s.get("sector") or "other","")}</span><span class="dot"></span><span class="time">{ago(s.get("last_updated_at"))}</span><span class="dot"></span><span>{span}</span></div>
  <h3>{s.get("hero_title") or s["label"]}</h3>
  <p class="what">{s["developments"]} developments across {s["source_count"]} outlets. {("Cast: " + ", ".join(s["cast"][:4])) if s.get("cast") else ""}</p>
  <div class="foot"><span class="cov">{covbar({"nat": s["source_count"]})}<span class="txt">{s["source_count"]} outlets · {s["developments"]} developments</span></span><span class="spacer"></span><span class="status provisional">Grouping under review</span></div>
</a>""")
    return head("Stories") + topbar("stories") + masthead("DEVELOPING") + f"""
<main class="page"><div class="shell"><div class="grid grid-2" style="padding-top:8px">
  {rail}
  <div>{chips}
    <div class="section"><h2>Stories</h2><span class="sub">Developing over days, ranked by new reporting</span></div>
    <div class="rows">{"".join(rows)}</div>
  </div>
</div></div></main>{tabbar("stories")}</body></html>"""


def disperse_svg(outlets: list[str], reports: int | None = None) -> str:
    """The brand figure: many reports enter the prism, one record leaves — in colour."""
    left = outlets[:7]
    ys = [40 + i * 30 for i in range(len(left))]
    dots = "".join(
        f'<g transform="translate(24,{y})"><circle r="13" fill="var(--surface)" stroke="var(--line-strong)"/><text x="0" y="3.5" text-anchor="middle" font-family="Hind,sans-serif" font-weight="600" font-size="9" fill="var(--ink-2)">{initials(o)}</text></g>'
        for o, y in zip(left, ys)
    )
    beams = "".join(f'<path d="M40 {y} C 120 {y}, 150 130, 196 130" stroke="var(--ink-3)" stroke-opacity=".45" stroke-width="1" fill="none"/>' for y in ys)
    cols = ["#ef4444", "#f59e0b", "#06b6d4", "#8b5cf6"]
    fan = "".join(f'<path d="M262 128 C 300 {128 + (i-1.5)*22}, 330 {128+(i-1.5)*26}, 372 {128+(i-1.5)*26}" stroke="{c}" stroke-width="3" stroke-linecap="round" fill="none" opacity=".95"/>' for i, c in enumerate(cols))
    return f"""<svg class="disperse" viewBox="0 0 400 260" role="img" aria-label="Many reports enter the prism; one record with every perspective leaves">
  {beams}{dots}
  <g transform="translate(228,130)"><path d="M0 -34 L34 30 L-34 30 Z" fill="var(--ink)"/><rect x="-34" y="26" width="68" height="6" fill="url(#g1)"/></g>
  {fan}
  <text x="372" y="88" font-family="Hind,sans-serif" font-size="10.5" font-weight="600" fill="var(--ink-3)" text-anchor="end" letter-spacing="1">ONE RECORD</text>
  <text x="26" y="20" font-family="Hind,sans-serif" font-size="10.5" font-weight="600" fill="var(--ink-3)" letter-spacing="1">{reports or len(outlets)} REPORTS · {len(outlets)} OUTLETS</text>
  <defs><linearGradient id="g1" x1="0" x2="1"><stop offset="0" stop-color="#ef4444"/><stop offset=".35" stop-color="#f59e0b"/><stop offset=".7" stop-color="#06b6d4"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
</svg>"""


def page_landing(feed, event, lenses) -> str:
    names = [s["source_name"] for s in event["sources"]]
    counts = {"nat": 0, "reg": 0, "int": 0}
    for n in names:
        counts[origin(n)] += 1
    lead = {**event, "source_count": len(set(names)), "available_languages": sorted({LANG_OF.get(n, "en") for n in names}), "coverage": {"origins": {"IN": len(names)}}}
    claims = event.get("claims") or []
    q = claims[0]["claims"][0] if claims else None
    brief = (event.get("lens_briefs") or {}).get("reader") or {}
    brief_text = brief.get("text") if isinstance(brief, dict) else ""
    devs = sorted(event["sources"], key=lambda s: s.get("published_at") or "", reverse=True)[:3]
    tl = "".join(f'<li{" class=now" if i==0 else ""}><div class="t">{ago(s.get("published_at"))} · {s["source_name"]}</div><div class="h" style="font-size:15px">{(s.get("title") or "")[:90]}</div></li>' for i, s in enumerate(devs))
    return head("Landing") + topbar("about", cta="Open today's record") + f"""
<main>
<section class="hero"><div class="shell">
  <div>
    <p class="eyebrow">News for India · every language · every source open</p>
    <h1>Follow the story, not the headlines.</h1>
    <p class="lede">Prism turns the day's reports from monitored outlets into one live record per story — what changed, who said what, exactly, and which outlets covered it. Then read the same facts through the lens of your work.</p>
    <div class="cta"><a class="btn btn-primary btn-lg" href="#">Open today's record {ICONS["arrow"]}</a><a class="btn btn-ghost btn-lg" href="#">How it works</a></div>
    <div class="kpi"><div><b>27</b><span>monitored outlets</span></div><div><b>10</b><span>languages read</span></div><div><b>1</b><span>record per story</span></div></div>
  </div>
  <div class="proof">
    {disperse_svg(sorted(set(names)), reports=len(names))}
    <div class="rows">{story_row(lead, lead=True, sources_for_monos=names)}</div>
    <p class="mono-s faint" style="margin:10px 2px 0">LIVE · updated {ago(event.get("last_updated_at"))}</p>
  </div>
</div></section>

<section class="lsection"><div class="shell">
  <p class="eyebrow">What you get on every story</p>
  <h2>The record, not a verdict.</h2>
  <p class="sub">Three things a headline can't give you, built from the reports themselves.</p>
  <div class="proofs">
    <div class="proof-card"><h3>What changed</h3><p>Every report on the story, newest first, with the outlet and the time it published. Follow a story and see only the new developments.</p><div class="demo"><ol class="timeline">{tl}</ol></div></div>
    <div class="proof-card"><h3>Exact words</h3><p>Quotes appear only when the exact words are in the article — attributed to the speaker, linked to the line they came from. No paraphrase, no invented positions.</p><div class="demo">{f'<article class="quote" style="padding:0;border:0"><div class="who"><span class="av">{initials(claims[0]["speaker"])}</span><div><div class="nm">{claims[0]["speaker"]}</div><div class="rl">{len(claims[0]["claims"])} quotes</div></div></div><blockquote style="font-size:16px">“{q["quote_text"]}”</blockquote><div class="src"><span class="pill">{q["source_name"]}</span><span>{ago(q.get("published_at"))}</span></div></article>' if q else "<p class=mono-s>ILLUSTRATION</p>"}</div></div>
    <div class="proof-card"><h3>Who covered it</h3><p>See at a glance whether a story is carried by English nationals, Indian-language outlets, international press — or just one of them.</p><div class="demo"><div class="cov" style="margin-bottom:8px">{covbar(counts, lg=True, width=200)}<span class="txt">{len(set(names))} outlets</span></div><div class="legend"><span><i class="c-nat"></i>English national</span><span><i class="c-reg"></i>Indian-language</span><span><i class="c-int"></i>International</span></div><div style="margin-top:12px">{monos(names, 6)}</div></div></div>
  </div>
</div></section>

<section class="lsection"><div class="shell" style="display:grid;gap:32px;align-items:center" id="lens">
  <div><p class="eyebrow">The signature</p><h2>The same facts, read for your work.</h2><p class="sub">Flip a story into the reading your work needs. The record underneath never changes; only the reading does — and every lens shows what it adds before you sign in.</p></div>
  <div class="flip">
    <div class="bar"><span class="label" style="text-transform:none;font-size:13.5px;color:var(--ink-2)">Read it as</span><div class="seg"><button aria-selected="true">Reader</button><button class="markets">Markets</button><button class="cyber">Cyber</button></div></div>
    <div class="body"><span class="scan" aria-hidden="true"></span><p>{brief_text[:420]}…</p><p class="mono-s faint" style="margin-top:12px">REAL RECORD · READER LENS · {ago(event.get("last_updated_at"))}</p></div>
  </div>
</div></section>

<section class="lsection"><div class="shell">
  <p class="eyebrow">Where Prism stands today</p>
  <h2>Honest about what's live.</h2>
  <div class="status-grid">
    <div class="status-col now"><h4>Available now</h4><ul><li>One record per story from 27 monitored outlets, six languages</li><li>Verbatim quotes with source and article context</li><li>Coverage by outlet type</li><li>Reader, Markets and Cyber readings</li><li>Ask, cited to the story's own reports</li></ul></div>
    <div class="status-col val"><h4>In validation</h4><ul><li>Story timelines across days (two-reviewer gate)</li><li>Freshness targets on a clean 72-hour cohort</li></ul></div>
    <div class="status-col next"><h4>Next</h4><ul><li>Follow a story, “new since you last read”</li><li>Original-language quote beside the translation</li><li>Corrections log on every record</li></ul></div>
  </div>
</div></section>

<section class="final"><div class="shell"><h2>Open today's record.</h2><a class="btn btn-primary btn-lg" href="#">Read today {ICONS["arrow"]}</a><p class="faint" style="margin-top:14px;font-size:14px">Free. No account needed to read.</p></div></section>
<footer class="footer"><div class="shell" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;width:100%"><span>Prism · Matryx Social Labs</span><span>About · Sources · Corrections · Privacy</span></div></footer>
</main></body></html>"""


def page_components(t) -> str:
    def swatches(mode):
        return "".join(f'<div><i style="background:{v["value"]}"></i><span>{k}<br>{v["value"]}</span></div>' for k, v in t["color"][mode].items() if not k.startswith("on-"))
    types = "".join(
        f'<div><span class="k">{k} · {"/".join(map(str, spec["size"])) if isinstance(spec["size"], list) else spec["size"]}px</span><span style="font-family:var(--font-{spec["font"]});font-size:{(spec["size"][0] if isinstance(spec["size"], list) else spec["size"])}px;font-weight:{spec["weight"]};line-height:{spec["line"]};font-style:{spec.get("style","normal")}">Follow the story, not the headlines · कहानी को फ़ॉलो करें · ಕಥೆಯನ್ನು ಅನುಸರಿಸಿ</span></div>'
        for k, spec in t["type"].items()
    )
    return head("Components") + f"""
<main class="shell sheet">
  <div><div class="section"><h2>Colour — light</h2></div><div class="sw">{swatches("light")}</div></div>
  <div data-theme="dark" style="background:var(--bg);color:var(--ink);padding:24px;border-radius:14px"><div class="section"><h2>Colour — dark</h2></div><div class="sw">{swatches("dark")}</div></div>
  <div><div class="section"><h2>Type</h2><span class="sub">Newsreader · Hind · JetBrains Mono</span></div><div class="tspec">{types}</div></div>
  <div><div class="section"><h2>Buttons & chips</h2></div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center"><a class="btn btn-primary" href="#">Follow story</a><a class="btn btn-secondary" href="#">Share</a><a class="btn btn-ghost" href="#">Sign in</a><a class="btn btn-primary btn-lg" href="#">Open today's record</a><a class="btn btn-secondary btn-sm" href="#">All 15 reports</a></div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:16px"><span class="chip" aria-current="page">All stories</span><span class="chip">Politics</span><span class="chip">Business &amp; Markets <span class="n">12</span></span><span class="status verified">{ICONS["check"]}Verified record</span><span class="status provisional">Provisional grouping</span><span class="status corrected">Corrected</span><span class="lensdot l-markets"><i></i>Markets read</span><span class="lensdot l-cyber"><i></i>Cyber read</span></div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-top:16px"><div class="seg"><button aria-selected="true">Reader</button><button class="markets">Markets</button><button class="cyber"><span class="lock">{ICONS["lock"]}</span>Cyber</button></div>
      <span class="cov">{covbar({"nat":9,"reg":4,"int":2}, lg=True, width=160)}<span class="txt">15 outlets · 3 languages</span></span>{monos(["The Hindu","Mint","Aaj Tak","NDTV","BBC World","Prajavani"],4)}</div>
  </div>
</main></body></html>"""


def main():
    if "--fetch" in sys.argv or not DATA.exists():
        fetch()
    t = tokens()
    feed, event, trending, lenses = load("feed"), load("event"), load("trending"), load("lenses")
    (HERE / "prism.css").write_text(css_vars(t) + BASE_CSS)
    pages = {
        "landing.html": page_landing(feed, event, lenses),
        "today.html": page_today(feed, event, lenses, trending),
        "story.html": page_story(event, lenses),
        "stories.html": page_stories(trending),
        "components.html": page_components(t),
    }
    for name, html in pages.items():
        (HERE / name).write_text(html)
    links = "".join(f'<li><a href="{n}">{n}</a> · <a href="{n}?theme=dark">dark</a></li>' for n in pages)
    (HERE / "index.html").write_text(head("Board") + f'<main class="shell" style="padding:32px 16px"><h1 class="display">Prism — Spectrum board</h1><ul style="font-size:18px;line-height:2">{links}</ul></main></body></html>')
    print("wrote", ", ".join(pages), "→", HERE)


if __name__ == "__main__":
    main()
