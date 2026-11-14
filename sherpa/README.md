# vits-piper-pi-pratham: Pali (pi) for sherpa-onnx

Pali text-to-speech with the Piper voice hi_IN-pratham-medium and a pronunciation lexicon, no espeak-ng.

- `pi-pratham-medium.onnx`: hi_IN-pratham-medium.onnx, unchanged weights, with sherpa-onnx metadata
  (model_type=vits, comment=piper, language=Pali, voice=pi, has_espeak=0, n_speakers=1, sample_rate=22050).
  It is the same network as sherpa-onnx's vits-piper-hi_IN-pratham-medium.
- `tokens.txt`: from the voice's phoneme_id_map (same as scripts/piper/add_meta_data.py).
- `lexicon-pi.txt`: `word || phones`, 196,890 entries: every word form (153,697) of the Pali Tipiṭaka
  (Mahāsaṅgīti edition: sutta, vinaya, abhidhamma), lowercase NFC IAST with niggahita ṁ, plus the same words spelled with ṃ, and capitalised where the first letter is not ASCII (Ānando: sherpa lowercases with towlower(), which leaves Ā as it is in the C locale).
  Phones come from the Dhamma.Gift Pali phonemizer (https://github.com/dhammagift/pali-tts, pali_ipa.py:
  tune(to_ipa(word, full_a=True))), the rules tuned in blind listening tests for this voice.
  "…pe…"/"…pa…" (an abridged passage) read as ", peyyāla,".

Recommended settings (what Dhamma.Gift uses): length_scale 1.15, noise_scale 0.6, noise_scale_w 0.7.

v2 (2026-11-14): the lexicon rebuilt on the phonemizer's rules r72 (13,859 entries changed since v1: every ph as p + h,
khuppipāsā and a few others from blind listening rounds). Checked on stock sherpa-onnx 2.0.1 (pip, with #4055 and #4075):
for 28 of 37 canon sentences (SN 56.11, SN 48.39, MN 10) the phonemes sherpa feeds the model are the same as
Dhamma.Gift's own server's. The other 9 differ only in the known limit below and in punctuation (a colon or semicolon
kept at the end, a dash dropped).

Known limit: entries are written as a word inside a phrase, so a word-final o is held long (as it should be mid-sentence);
right before a full stop it comes out longer than Dhamma.Gift's own server makes it. Pauses that depend on the next
word (a one-syllable word before a vowel: "so, evamāha") cannot be expressed in a per-word lexicon.

## Licenses
- Voice weights: MIT (rhasspy/piper-voices). Its MODEL_CARD lists the dataset license as CC BY-NC-SA 4.0.
- Lexicon and phonemizer: MIT, Copyright (c) 2026 Dhamma.Gift (https://github.com/dhammagift/pali-tts/blob/main/LICENSE).
- Word list: the Mahāsaṅgīti Pali Tipiṭaka as published in SuttaCentral bilara-data; see https://suttacentral.net/licensing.
