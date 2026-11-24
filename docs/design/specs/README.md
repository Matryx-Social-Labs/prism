# Design specs for the new surfaces

Six surfaces Prism does not have yet, decided on paper before any is built (programme task T-047, 2026-11-24).
A spec here is **binding** on the task that builds the surface: it does not invent a layout, a state or a
sentence the spec does not give. `DESIGN.md` still governs everything a spec does not mention.

| # | Surface | Spec | Comp | Built by |
|---|---|---|---|---|
| 1 | Today's edition and its end block | [01-edition.md](01-edition.md) | `comps/edition.html`, `edition-states.html`; the three it was chosen from: `edition-a`, `-b`, `-c` | T-051 (document: T-038) |
| 2 | Follow, "Following", the Following tab, the free limit, "new since you read" | [02-follow.md](02-follow.md) | `comps/follow-b.html` (chosen), `-a`, `-c`, `following.html` | T-050 |
| 3 | The notification explanation and settings | [03-notifications.md](03-notifications.md) | `comps/notifications.html` | T-053 (sending: T-036) |
| 4 | The language step | [04-language.md](04-language.md) | `comps/language.html` | T-054 |
| 5 | The shell by width, with a navigation rail on tablets | [05-tablet-shell.md](05-tablet-shell.md) | `comps/shell.html` | T-042 |
| 6 | The story page's "Where it stands" header | [06-story-header.md](06-story-header.md) | `comps/story-header.html` | T-007, then T-052 |

**Sign-off.** D-21 delegates approval to this task's design review. The founder reads the specs and may
overrule any line; work proceeds meanwhile. Each spec ends with "Decided here", the choices a reader of the
spec is most likely to want to change.

## How to read a spec

Every spec has the same sections: purpose · where it lives · content in order · states · copy · layout at
compact, medium and expanded · motion · accessibility · primitives · depends on · decided here · references.

- **Size classes** are the programme's five (PLAN §4.2): compact < 600 · medium 600–1023 · expanded 1024–1279
  · large 1280–1535 · xlarge ≥ 1536. A spec gives compact, medium and expanded; large and xlarge are expanded
  unless the spec says otherwise.
- **Copy** is given as the exact English sentence, with slots in braces: `{k} outlets`. A slot is filled from
  live data or it is not printed; a spec never supplies a figure. Hindi strings are written by T-054's
  catalogue and reviewed by a native reader, not here.
- **Primitives** are named as `DESIGN.md` · Components names them (Button, Chip, Sheet, Toast, ToggleRow …).
  T-041 builds them; a surface built before T-041 lands uses the `.p-*` class of the same name.
- **A state the spec lists is required.** A state it does not list does not exist: ask, do not invent.

## The comps

`comps/*.html` are pictures, as plain HTML, of what a spec describes. They are not the product and nothing
imports them.

- Open them through a server at the repository root, because they link the app's own stylesheet for the real
  tokens and `.p-*` classes:
  `python3 -m http.server 8765` then `http://localhost:8765/docs/design/specs/comps/edition.html`.
  Add `?theme=dark` for the dark ground. If `web/src/app/globals.css` moves, fix the one `@import` at the top
  of `comps/comp.css`.
- The news in them is real: `comps/data.json` holds records, quotes and one story as the public API returned
  them on 2026-11-24 at about 17:50 UTC, unedited. It is a snapshot, not live.
- Anything a comp tags **ILLUSTRATION** is drawn, not data: a reader's follows, "new since you read", a limit
  reached, a notification, a Hindi interface string, an error. Those tags and the comp banner never ship
  (`DESIGN.md` · Content rules).
- Where a comp and its spec disagree, the spec is right.

## Why HTML and not generated mock-ups

The task named the `design-shotgun` and `design-html` skills. `design-shotgun` produces raster mock-ups
through a paid image service and waits for a person at a comparison board; the task states no budget and
nobody was at the keyboard, so the three variants of the edition and of the follow control were drawn as HTML
on the real tokens instead, and judged by the design review. `design-html` writes finished page markup; the
build tasks do that, from these specs.

References are in `~/prism-program/design-refs/` (one file per surface, plus `board.md`, which is the design
audit's §7). They are for structure and interaction only.
