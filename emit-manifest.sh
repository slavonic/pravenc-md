#!/usr/bin/env bash
# Emit a change manifest for pravenc-rag's `pravenc-index update`.
#
# Install into the pravenc-md corpus repo (NOT pravenc-rag). Run it there,
# where full history exists, so the indexing side can stay a shallow checkout.
#
#   ./emit-manifest.sh <prev_ref> [new_ref]
#   ./emit-manifest.sh v2.3 v2.4
#   ./emit-manifest.sh v2.3            # new_ref defaults to HEAD
#
# Writes updates/<new_ref>.txt containing `git diff --name-status` over
# articles/. Commit it (so a submodule consumer gets it for free) or attach it
# as a release asset — either works.
set -euo pipefail

PREV="${1:?usage: emit-manifest.sh <prev_ref> [new_ref]}"
NEW="${2:-HEAD}"
NAME="${NEW#refs/tags/}"
[ "$NAME" = "HEAD" ] && NAME="$(git rev-parse --short HEAD)"

mkdir -p updates
OUT="updates/${NAME}.txt"
git diff --name-status "${PREV}..${NEW}" -- articles/ > "$OUT"
echo "wrote ${OUT} ($(wc -l < "$OUT" | tr -d ' ') changed article files)"
