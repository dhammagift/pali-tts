#!/usr/bin/env bash
# Kaggle GPU queue for 2026-10-17 (owner: «завтра на gpu запустим»), on f3, one job at a time, each smoke first:
# M1 re-read with stress marks -> dataset; after the weekly quota reset: Miles demo (2 h), then the M1 student (2:30).
# A failed or output-less step stops the queue. Log: /root/gpu-queue.log
set -uo pipefail
cd /var/www/pali-tts
K=(/root/.local/bin/uvx --python 3.12 kaggle@2.2.4)
export KAGGLE_API_TOKEN=$(cat /root/.secrets/kaggle)
log() { echo "$(date -u +%FT%H:%M) $*"; }
wait_kernel() {  # $1 kernel; until it leaves queued/running
  while :; do
    st=$("${K[@]}" kernels status "$1" 2>&1 | tail -1)
    case "$st" in *COMPLETE*) log "$1 complete"; return 0 ;; *ERROR*|*CANCEL*) log "$1 failed: $st"; return 1 ;; esac
    sleep 300
  done
}
fetch() {  # $1 kernel, $2 dir: outputs without the cache; the onnx must be there
  mkdir -p "$2" && "${K[@]}" kernels output "$1" -p "$2" --file-pattern '(\.log|out/.*)$' >/dev/null 2>&1
  ls "$2"/out/*.onnx >/dev/null 2>&1 || { log "$1: no onnx in $2"; return 1; }
}
push_miles() {  # $1 = 1 for smoke
  d=$(mktemp -d); cp kaggle-en-miles/* "$d/"
  [ "$1" = 1 ] && sed -i "s/^SMOKE = .*/SMOKE = True/" "$d/train.py"
  "${K[@]}" kernels push -p "$d"; rm -rf "$d"
}

until grep -q '^done' /root/st-m1s/gen.log 2>/dev/null; do sleep 300; done
log "M1 re-read: $(tail -1 /root/st-m1s/gen.log)"
.venv/bin/python make_ru_voice_dataset.py /root/st-m1s /root/st-m1s/data ru-stm1s-voice-data || exit 1
(cd /root/st-m1s/data && "${K[@]}" datasets create -p . --dir-mode zip) || exit 1
log "dataset ru-stm1s-voice-data up"

until [ "$(date -u +%F)" \> "2026-10-16" ]; do sleep 300; done
sleep 600  # the reset itself
log "quota reset: Miles smoke"
push_miles 1 && wait_kernel dhammagift/en-miles-voice-train && fetch dhammagift/en-miles-voice-train /root/en-miles/smoke || exit 1
log "Miles full"
push_miles 0 && wait_kernel dhammagift/en-miles-voice-train && fetch dhammagift/en-miles-voice-train /root/en-miles/run || exit 1
log "M1s smoke"
(cd kaggle-ru-stm1 && SET=stm1s SMOKE=1 ./push_ru_stm1.sh ruslan) && wait_kernel dhammagift/ru-stm1s-ruslan \
  && fetch dhammagift/ru-stm1s-ruslan /root/st-m1/runs/ruslan-s-smoke || exit 1
log "M1s full"
(cd kaggle-ru-stm1 && SET=stm1s ./push_ru_stm1.sh ruslan) && wait_kernel dhammagift/ru-stm1s-ruslan \
  && fetch dhammagift/ru-stm1s-ruslan /root/st-m1/runs/ruslan-s || exit 1
log "all done"
