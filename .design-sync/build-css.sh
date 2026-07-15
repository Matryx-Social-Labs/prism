#!/bin/sh
# Compiles the app's Tailwind stylesheet for the design-system bundle.
# Run from the repo root before .ds-sync/package-build.mjs (cfg.buildCmd).
set -e
mkdir -p .design-sync/.cache
# Google-fonts @import must stay the first rule; then font vars, then the app
# stylesheet (its @tailwind directives expand in place).
cat .design-sync/fonts.css web/src/app/globals.css > .design-sync/.cache/css-input.css
cd web
npx tailwindcss -c tailwind.config.ts \
  -i ../.design-sync/.cache/css-input.css \
  -o .ds-tailwind.css \
  --content "src/**/*.{ts,tsx}"
echo "compiled: web/.ds-tailwind.css"
