# Prism design system — conventions

Prism is a news-intelligence product: adaptive light/dark, editorial typography, a spectrum
gradient as the brand accent, and amber/cyan/violet lens colors. The governing rule
(DESIGN.md): **chrome is monochrome — color only ever means a lens is speaking.**

## Setup

No provider is required. Theme is controlled by `data-theme="light" | "dark"` on the **root
element** (`<html>`); without it, `prefers-color-scheme` decides. All tokens and component CSS
arrive via `styles.css`'s import closure. Fonts (Fraunces for display, General Sans for UI)
load from the Google Fonts `@import` in the stylesheet and are exposed as `--font-display` and
`--font-ui`.

## Styling idiom

Tailwind utility classes for layout/spacing/radius (`flex`, `gap-2`, `rounded-2xl`, `px-2`,
`py-0.5`, `text-xs`, `font-semibold`, `space-y-3`) **plus inline `style` for anything colored,
always through tokens** — never hex values:

- Surfaces: `var(--bg)`, `var(--bg-elevated)` (cards), `var(--bg-sunken)` (chips/skeletons)
- Text: `var(--ink)`, `var(--ink-muted)`, `var(--ink-faint)`
- Borders: `var(--line)`, `var(--line-strong)`
- Lens colors: `var(--lens-general)` / `var(--lens-general-bg)` (amber), `var(--lens-cyber)` /
  `var(--lens-cyber-bg)` (cyan), `var(--lens-finance)` / `var(--lens-finance-bg)` (violet)
- Signals: `var(--danger)` / `var(--danger-bg)`, `var(--up)` / `var(--up-bg)`
- Brand gradient: `var(--spectrum)`; gradient text via the `spectrum-text` class

Recurring pieces: chips/badges are `rounded-full px-2 py-0.5 text-xs font-semibold` with a
token background; cards are `rounded-2xl border p-5` with
`style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}`; display headings set
`style={{ fontFamily: "var(--font-display), serif" }}`.

Motion classes (already reduced-motion-safe): `card-hover` (lift on hover), `reveal` +
`<Reveal>` (scroll reveal), `stagger` (list entry), `fade-swap` (content swap), `beam-in` /
`beam-out` / `prism-glow` (hero figure).

## Where the truth lives

Read `styles.css` → `_ds_bundle.css` (all tokens for both themes + compiled utilities) before
inventing any style. Per-component usage lives in each `components/general/<Name>/<Name>.prompt.md`.

## Idiomatic composition

```tsx
import { ThreadRail } from "prism-web";

<div className="card-hover rounded-2xl border p-5"
     style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
  <span className="rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide"
        style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
    politics
  </span>
  <h2 className="mt-2 font-semibold leading-snug">Headline goes here</h2>
  <ThreadRail
    thread={{ upstream: [], downstream: [] }}
    currentTitle="Headline goes here"
  />
</div>
```
