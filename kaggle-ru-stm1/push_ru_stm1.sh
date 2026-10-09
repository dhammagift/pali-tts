#!/usr/bin/env bash
# One Kaggle kernel per base voice from train.py: ./push_ru_stm1.sh ruslan [denis dmitri] [MAX_TIME=00:02:30:00]
# SMOKE=1 ./push_ru_stm1.sh ruslan -> an 8-minute run that only proves the environment.
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
import json, sys
d, base = sys.argv[1:]
m = json.load(open('kernel-metadata.json'))
m['id'] = f'dhammagift/ru-stm1-{base}'; m['title'] = f'ru-stm1-{base}'
json.dump(m, open(f'{d}/kernel-metadata.json', 'w'))
PY
  "${K[@]}" kernels push -p "$d"
  rm -rf "$d"
done
