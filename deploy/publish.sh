#!/usr/bin/env bash
# The listening pages and the owner's votes stay on the main server (test.dhamma.gift/old/pali-tts, save.php
# writes votes/ and takes/ there); the work runs on f3. This moves pages + audio there and the votes back.
# Usage: deploy/publish.sh push   - site/*.html and out/ to the main server
#        deploy/publish.sh votes  - votes/ (and the owner's recorded takes/) from the main server
set -euo pipefail
cd "$(dirname "$0")/.."
MAIN=root@94.126.201.8
SSH="ssh -p 1000 -o BatchMode=yes"
case "${1:-}" in
  push)  rsync -az -e "$SSH" site/*.html "$MAIN:/var/www/pali-tts/site/"
         rsync -az -e "$SSH" --exclude 'ears/' --exclude 'mms/' out/ "$MAIN:/var/www/pali-tts/out/" ;;
  votes) rsync -az -e "$SSH" "$MAIN:/var/www/pali-tts/votes/" votes/
         rsync -az -e "$SSH" "$MAIN:/var/www/pali-tts/takes/" takes/ ;;  # never --delete: these are the owner's
  *) echo "usage: $0 push|votes" >&2; exit 2 ;;
esac
