#!/usr/bin/env bash
# Rebuild everything from the raw USAspending zips. Usage: bash run_all.sh path/to/*.zip  [--final]
set -euo pipefail
cd "$(dirname "$0")/code"
FINAL=""; ZIPS=()
for a in "$@"; do [[ "$a" == "--final" ]] && FINAL="--final" || ZIPS+=("$(realpath "$a")"); done
[[ ${#ZIPS[@]} -gt 0 ]] && python3 01_ingest.py "${ZIPS[@]}"
python3 02_build.py
python3 03_qa.py
python3 04_figures.py $FINAL
python3 05_document.py $FINAL
