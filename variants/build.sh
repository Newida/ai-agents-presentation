#!/usr/bin/env bash
# Build main.tex in five optional themes, without changing the default PDF.
# Usage: variants/build.sh [neon terminal swiss aurora paper]
set -euo pipefail
cd "$(dirname "$0")/.."
names=("$@")
if [ ${#names[@]} -eq 0 ]; then names=(neon terminal swiss aurora paper); fi
for name in "${names[@]}"; do
  case "$name" in neon|terminal|swiss|aurora|paper) ;; *) echo "Unknown design: $name" >&2; exit 2 ;; esac
done
mkdir -p variants/.build
# Reference layout for the overlay/content checks; main.pdf is never overwritten.
for pass in 1 2; do
  if ! pdflatex -interaction=nonstopmode -halt-on-error -jobname=original \
    -output-directory=variants/.build main.tex >variants/.build/original.stdout 2>&1; then
    cat variants/.build/original.stdout >&2
    exit 1
  fi
done
for name in "${names[@]}"; do
  # Beamer's built-in fit option keeps dense slides within the new headers/footers.
  # Only generated copies receive it; wording and all overlay specifications stay intact.
  python3 - "$name" <<'PY'
from pathlib import Path
import sys
import re
name = sys.argv[1]
s = Path('main.tex').read_text()
s = s.replace(r'\begin{frame}', r'\begin{frame}[shrink=0]')
s = re.sub(r'(\\item(?:<[^>]*>)?)\[\+\]', r'\1[\\deckplus]', s)
s = re.sub(r'(\\item(?:<[^>]*>)?)\[--\]', r'\1[\\deckminus]', s)
Path(f'variants/.build/{name}.tex').write_text(r'\def\decktheme{' + name + '}\n' + s)
PY
  for pass in 1 2; do
    if ! pdflatex -interaction=nonstopmode -halt-on-error -output-directory=variants/.build \
      "variants/.build/$name.tex" >"variants/.build/$name.stdout" 2>&1; then
      cat "variants/.build/$name.stdout" >&2
      exit 1
    fi
  done
  if grep -q '^Overfull' "variants/.build/$name.log"; then
    grep -A4 '^Overfull' "variants/.build/$name.log" >&2
    echo "Layout overflow in $name (see variants/.build/$name.log)" >&2
    exit 1
  fi
  cp "variants/.build/$name.pdf" "variants/$name.pdf"
  pages=$(pdfinfo "variants/$name.pdf" | awk '/^Pages:/{print $2}')
  echo "OK variants/$name.pdf ($pages pages, no overflow)"
done
python3 variants/check.py "${names[@]}"
python3 variants/sheet.py "${names[@]}"
