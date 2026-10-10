// espeak-ng for DG offline voices (WebAssembly): the same calls as Piper's espeakbridge.c (piper-tts 1.8.0),
// so the browser gets the phonemes the voice service gets. Build: web/espeak/build.sh
#include <stdlib.h>
#include <string.h>
#include <espeak-ng/speak_lib.h>
#include <emscripten/emscripten.h>

#define CLAUSE_INTONATION_FULL_STOP 0x00000000
#define CLAUSE_INTONATION_COMMA 0x00001000
#define CLAUSE_INTONATION_QUESTION 0x00002000
#define CLAUSE_INTONATION_EXCLAMATION 0x00003000
#define CLAUSE_TYPE_CLAUSE 0x00040000
#define CLAUSE_TYPE_SENTENCE 0x00080000
#define CLAUSE_PERIOD (40 | CLAUSE_INTONATION_FULL_STOP | CLAUSE_TYPE_SENTENCE)
#define CLAUSE_COMMA (20 | CLAUSE_INTONATION_COMMA | CLAUSE_TYPE_CLAUSE)
#define CLAUSE_QUESTION (40 | CLAUSE_INTONATION_QUESTION | CLAUSE_TYPE_SENTENCE)
#define CLAUSE_EXCLAMATION (45 | CLAUSE_INTONATION_EXCLAMATION | CLAUSE_TYPE_SENTENCE)
#define CLAUSE_COLON (30 | CLAUSE_INTONATION_FULL_STOP | CLAUSE_TYPE_CLAUSE)
#define CLAUSE_SEMICOLON (30 | CLAUSE_INTONATION_COMMA | CLAUSE_TYPE_CLAUSE)

EMSCRIPTEN_KEEPALIVE int dg_init(const char *data_dir) {
  return espeak_Initialize(AUDIO_OUTPUT_SYNCHRONOUS, 0, data_dir, 0);
}

EMSCRIPTEN_KEEPALIVE int dg_voice(const char *name) { return espeak_SetVoiceByName(name); }

// One line per clause: phonemes \t terminator \t 1 if it ends a sentence. The caller frees the result.
EMSCRIPTEN_KEEPALIVE char *dg_phonemes(const char *text) {
  size_t cap = 256, len = 0;
  char *out = malloc(cap);
  out[0] = 0;
  while (text != NULL) {
    int terminator = 0;
    const char *term = "";
    const char *ph = espeak_TextToPhonemesWithTerminator((const void **)&text, espeakCHARS_AUTO, espeakPHONEMES_IPA, &terminator);
    terminator &= 0x000FFFFF;
    if (terminator == CLAUSE_PERIOD) term = ".";
    else if (terminator == CLAUSE_QUESTION) term = "?";
    else if (terminator == CLAUSE_EXCLAMATION) term = "!";
    else if (terminator == CLAUSE_COMMA) term = ",";
    else if (terminator == CLAUSE_COLON) term = ":";
    else if (terminator == CLAUSE_SEMICOLON) term = ";";
    size_t need = len + (ph ? strlen(ph) : 0) + strlen(term) + 5;
    if (need > cap) {
      while (need > cap) cap *= 2;
      out = realloc(out, cap);
    }
    len += sprintf(out + len, "%s\t%s\t%d\n", ph ? ph : "", term, (terminator & CLAUSE_TYPE_SENTENCE) == CLAUSE_TYPE_SENTENCE);
  }
  return out;
}
