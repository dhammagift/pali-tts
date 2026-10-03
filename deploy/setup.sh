#!/usr/bin/env bash
# Bring up the DG voice service on a fresh server (e.g. the backup one):
#   git clone git@github.com:dhammagift/pali-tts.git /var/www/pali-tts && /var/www/pali-tts/deploy/setup.sh
# Needs: python3 (3.9+), python3-venv, ffmpeg, curl. Idempotent: re-running only adds what is missing.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q piper-tts numpy

mkdir -p models
grep -v '^#' deploy/models.txt | while read -r stem path; do
    [ -n "$stem" ] || continue
    for ext in onnx onnx.json; do
        [ -s "models/$stem.$ext" ] || curl -sfL -o "models/$stem.$ext" \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/$path/$stem.$ext"
    done
done

cp deploy/pali-tts.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now pali-tts
sleep 5
curl -s localhost:3011/health && echo
