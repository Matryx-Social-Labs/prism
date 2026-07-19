# Prism — agent instructions

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

Core rules worth restating:
- Tagline is "One story. Every perspective." Never enumerate lens names in generic/marketing copy — the lens set grows (pickers render whatever /api/v1/lenses returns).
- Chrome is monochrome; color only ever means a lens is speaking (lens hues: general amber, cyber cyan, markets violet — discrete, never gradients).
- Three type voices: Fraunces (display), General Sans (UI), IBM Plex Mono (provenance only: timestamps, sources, citations, funding labels, chain dates).
- The signature motion is the re-typeset lens flip (scan line + re-ink, 500ms, reduced-motion collapses to instant swap). Never a crossfade.
