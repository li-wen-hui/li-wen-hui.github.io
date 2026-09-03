#!/usr/bin/env bash
set -euo pipefail
python scripts/sync_sources.py
python scripts/build_site.py
printf '\nBuilt locally in ./dist\nRun: python -m http.server 8000 -d dist\n'
