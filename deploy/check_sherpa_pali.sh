#!/usr/bin/env bash
# Daily from cron on f3 (owner 2026-11-17: no Claude session or model tokens for a watch): once sherpa-onnx publishes a
# release after v2.0.1 (the first with PR #4203), tell the owner in the admin Telegram chat (the dgift bot, as
# scripts/seo-weekly.py does) - any release, with or without Pali in it (owner: «а вдруг они выпустят релиз, а нашего там
# не будет»); then once more when its Pali TTS-engine APK is on Hugging Face, or a week on without it. Flag files in
# cache/; no release yet: nothing (owner: «пока нет релиза, можешь ничего не присылать»).
set -euo pipefail
cd "$(dirname "$0")/.."
FOUND=cache/sherpa-pali-found
MISSING=cache/sherpa-pali-missing
[ -e "$FOUND" ] && exit 0
comment() {  # to the admin chat of the dgift bot; the token never leaves the config file
  python3 - "$1" <<'PY'
import json, sys, urllib.parse, urllib.request
c = json.load(open('/var/www/telegram_bot/config.dgift_bot.json'))
admin = c['ADMIN_ID'][0] if isinstance(c['ADMIN_ID'], list) else c['ADMIN_ID']
urllib.request.urlopen(f"https://api.telegram.org/bot{c['TOKEN']}/sendMessage",
                       urllib.parse.urlencode({'chat_id': admin, 'text': sys.argv[1]}).encode(), timeout=30)
PY
}
rel=$(curl -fsS https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/latest)
ver=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))' <<<"$rel")
[ "$ver" = "2.0.1" ] && exit 0
apk="https://huggingface.co/csukuangfj2/sherpa-onnx-apk/resolve/main/tts-engine-new/$ver/sherpa-onnx-$ver-arm64-v8a-pli-tts-engine-vits-piper-hi_IN-pratham-medium.apk"
lex=$(curl -s -o /dev/null -w '%{http_code}' -IL https://github.com/dhammagift/pali-tts/releases/download/sherpa-pi-pratham-v2/lexicon-pi.txt)
has=$(curl -s -o /dev/null -w '%{http_code}' -IL "$apk")
if [ ! -e "cache/sherpa-release-$ver" ]; then
  [ "$has" = 200 ] && now='APK с пали уже есть' || now='APK с пали пока нет (их собирают через несколько дней после релиза; напишу, когда появится или если через неделю его не будет)'
  comment "Вышел sherpa-onnx $ver: https://github.com/k2-fsa/sherpa-onnx/releases/tag/v$ver . $now."
  touch "cache/sherpa-release-$ver"
fi
if [ "$has" = 200 ]; then
  comment "APK с пали вышел: sherpa-onnx $ver, $apk (наш словарь lexicon-pi.txt в релизе: HTTP $lex)"
  touch "$FOUND"
else
  # their APKs come some days after the release: complain once if a week later there is still no Pali one
  age=$(python3 -c 'import json,sys,datetime as d; t=d.datetime.fromisoformat(json.load(sys.stdin)["published_at"].replace("Z","+00:00")); print((d.datetime.now(d.timezone.utc)-t).days)' <<<"$rel")
  if [ "$age" -ge 7 ] && [ ! -e "$MISSING" ]; then
    comment "sherpa-onnx $ver вышел $age дн. назад, а APK с пали нет: $apk (словарь: HTTP $lex). Проверить их сборку apk-tts-engine."
    touch "$MISSING"
  fi
fi
