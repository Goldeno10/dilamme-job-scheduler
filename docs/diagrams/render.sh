#!/usr/bin/env bash
# Regenerate PNG diagrams from Mermaid source files.
set -euo pipefail
cd "$(dirname "$0")"

CONFIG="-p puppeteer-config.json"

for mmd in *.mmd; do
  png="${mmd%.mmd}.png"
  echo "Rendering $mmd -> $png"
  npx -y @mermaid-js/mermaid-cli $CONFIG -i "$mmd" -o "$png" -b transparent -w 1200
done

echo "Done."
