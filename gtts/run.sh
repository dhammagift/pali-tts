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
  adb exec-out run-as gift.dhamma.gtts cat files/out/done.txt 2>/dev/null | grep -q done && break
done
adb exec-out run-as gift.dhamma.gtts tar c -C files out > out/out.tar
adb logcat -d -s GTTS TextToSpeech TtsService > out/logcat.txt
true
