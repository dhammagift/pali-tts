#!/usr/bin/env bash
# One Kaggle kernel per base voice from train.py: ./push_ru_stm1.sh ruslan [denis dmitri] [MAX_TIME=00:02:30:00]
# SMOKE=1 ./push_ru_stm1.sh ruslan -> an 8-minute run that only proves the environment.
# SET=stm1s: kernel ru-stm1s-<base> on dataset ru-stm1s-voice-data (M1 re-read with stress marks, 2026-10-16).
# RESUME=1: goes on from the Kaggle dataset dhammagift/ru-stm1-ckpt-<base> (that run's last.ckpt), as the same kernel.
#   MAX_TIME then counts from that run's start (Lightning restores its timer: ruslan's last.ckpt has 2:18 in it), not SMOKE.
set -euo pipefail
cd "$(dirname "$0")"
K=(/root/.local/bin/uvx --python 3.12 kaggle@2.2.4)
export KAGGLE_API_TOKEN=$(cat /root/.secrets/kaggle)
TIME=${MAX_TIME:-00:02:30:00}
for base in "$@"; do
  d=$(mktemp -d)
  sed -e "s/^BASE = .*/BASE = '$base'/" -e "s/'00:02:30:00'/'$TIME'/" train.py > "$d/train.py"
  [ "${SMOKE:-0}" = 1 ] && sed -i "s/^SMOKE = .*/SMOKE = True/" "$d/train.py"
  python3 - "$d" "$base" <<'PY'
import json, os, sys
d, base = sys.argv[1:]
m = json.load(open('kernel-metadata.json'))
st = os.environ.get('SET', 'stm1')
m['id'] = f'dhammagift/ru-{st}-{base}'; m['title'] = f'ru-{st}-{base}'
m['dataset_sources'] = [f'dhammagift/ru-{st}-voice-data']
if os.environ.get('RESUME') == '1':
    m['dataset_sources'].append(f'dhammagift/ru-{st}-ckpt-{base}')
json.dump(m, open(f'{d}/kernel-metadata.json', 'w'))
PY
  "${K[@]}" kernels push -p "$d"
  rm -rf "$d"
done
