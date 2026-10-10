#!/bin/bash
# espeak-ng 724808c (the commit piper-tts 1.8.0 builds) as WebAssembly for DG's offline en/ru voices -> web/espeak/espeak.mjs
# + espeak.wasm. Needs emsdk (/root/emsdk on f3) and an espeak-ng checkout at that commit built with emcmake:
#   git clone https://github.com/espeak-ng/espeak-ng && git -C espeak-ng checkout 724808c && mkdir espeak-ng/build-wasm && cd espeak-ng/build-wasm
#   emcmake cmake .. -DBUILD_SHARED_LIBS=OFF -DUSE_ASYNC=OFF -DUSE_MBROLA=OFF -DUSE_LIBSONIC=OFF -DUSE_LIBPCAUDIO=OFF \
#     -DUSE_KLATT=OFF -DUSE_SPEECHPLAYER=OFF -DCMAKE_BUILD_TYPE=Release \
#     "-DCMAKE_C_FLAGS=-U__WINT_TYPE__ -D__WINT_TYPE__=unsigned\ int -Wno-macro-redefined -Wno-builtin-macro-redefined"
#   emmake make espeak-ng          (wint_t: emscripten's int clashes with espeak's ucd_isalnum(uint32_t) declarations)
# Usage: ESPEAK=/root/espeak-wasm/espeak-ng web/espeak/build.sh
set -e
source /root/emsdk/emsdk_env.sh >/dev/null 2>&1
D=$(dirname "$0")
emcc -O2 "$D/dg_espeak.c" -I"$ESPEAK/src/include" "$ESPEAK/build-wasm/src/libespeak-ng/libespeak-ng.a" \
  "$ESPEAK/build-wasm/src/ucd-tools/libucd.a" -o "$D/espeak.mjs" \
  -sMODULARIZE -sEXPORT_ES6 -sENVIRONMENT=web,worker,node -sALLOW_MEMORY_GROWTH -sFORCE_FILESYSTEM \
  -sEXPORTED_FUNCTIONS=_dg_init,_dg_voice,_dg_phonemes,_free \
  -sEXPORTED_RUNTIME_METHODS=FS,ccall,UTF8ToString,stringToNewUTF8 -sINCOMING_MODULE_JS_API=wasmBinary,locateFile,print,printErr
ls -la "$D/espeak.mjs" "$D/espeak.wasm"
