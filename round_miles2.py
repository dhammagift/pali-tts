"""Round miles2: Yojanāni (Miles) v1 (100 takes) against v2 (185 takes, 2:30), blind, on 6 lines of DG's own English
translation ("o", SN 56.11 and SN 54.1), read the way tts_server reads English (abbreviations first, sentence by
sentence, 0.35 s between). English page (build_page LANG='en'): Miles has no Russian.
Usage (on f3): .venv/bin/python round_miles2.py [v2 model] -> out/miles2/; then build_page.py with ROUND = 'miles2'
"""
import json
import os
import re
import sys

import numpy as np
from piper import PiperVoice, SynthesisConfig

from respell import en_expand, en_phonemes
from round_st1 import mp3

OUT = 'out/miles2'
V2 = sys.argv[1] if len(sys.argv) > 1 else '/root/en-miles/run2/out/en_miles-medium.onnx'
TEXTS = ['And with this spoken explanation for the Venerable Koṇḍañña the dustless stainless dhamma-vision arose:',
         '“Whatever phenomenon of accumulating, all that is phenomenon of elimination.”',
         'And how, monks, is remembrance of breathing developed? How is it multiplied to be great-fruitful, to be great-beneficial?',
         'Having heard the sound of the local devas, the devas of the Four Great Kings proclaimed:',
         '\'Gladdening the mind I-will-breathe-out\' he trains, \'gladdening the mind I-will-breathe-in\' he trains.',
         'Thus to the Venerable Koṇḍañña ‘Koṇḍañña the one who understood’ the name arose.']
CFG = SynthesisConfig(length_scale=1.0, noise_scale=0.6, noise_w_scale=0.7)  # tts_server's settings for a translation voice


def read(voice, text):
    parts = []
    for sent in re.split(r'(?<=[.?!;:])\s+', en_expand(text).strip()):
        ph = en_phonemes(voice, sent)
        parts += [voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph), CFG), np.zeros(int(voice.config.sample_rate * 0.35), np.float32)]
    return np.concatenate(parts), voice.config.sample_rate


if __name__ == '__main__':
    voices = [('v1', 'Yojanāni v1 (100 lines, now in DG)', PiperVoice.load('models/en_miles-medium.onnx')),
              ('v2', 'Yojanāni v2 (185 lines)', PiperVoice.load(V2, config_path=V2 + '.json'))]
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, label, voice in voices:
            f = f'en{i}.{vid}.mp3'
            mp3(*read(voice, text), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ best; ✓ ok; ✗ bad. Tap a word that is read wrong'})
    json.dump({'round': 'miles2', 'sections': [{'id': 'en', 'title': 'Yojanāni v1 or v2, blind', 'multi_best': False,
                                                'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
