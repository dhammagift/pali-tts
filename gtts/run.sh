#!/bin/bash
# Runs inside the emulator step of .github/workflows/gtts.yml: install the app, let it synthesise every line, pull the wavs.
set -x
mkdir -p out
adb shell pm list packages | grep -i -E 'tts|speech|googlequicksearch' > out/packages.txt
adb shell dumpsys package com.google.android.tts | grep -E 'versionName|lastUpdateTime' >> out/packages.txt
adb install -r gtts/build/outputs/apk/debug/gtts-debug.apk
adb shell am start -n gift.dhamma.gtts/.Main
for i in $(seq 1 ${MINUTES:-30}0); do  # every 6 s
  sleep 6
  adb exec-out run-as gift.dhamma.gtts cat files/out/done.txt 2>/dev/null | grep -q '^done ' && break  # not just 'done': cat's error names done.txt
  if [ $((i % 100)) -eq 0 ]; then  # every 10 min: how many lines are done, and the wavs so far (a crash keeps them)
    set +x
    echo "progress $(adb shell run-as gift.dhamma.gtts ls files/out | grep -c wav) wavs after $((i / 10)) min"
    adb exec-out run-as gift.dhamma.gtts tar c -C files out > out/out.tar
    set -x
  fi
done
adb exec-out run-as gift.dhamma.gtts tar c -C files out > out/out.tar
adb logcat -d -s GTTS TextToSpeech TtsService > out/logcat.txt
true
