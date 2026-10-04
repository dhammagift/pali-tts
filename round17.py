"""Round 17: a vowel-final word before a vowel-initial one ("So evamāha" came out as "сори эвамаха": the
voice glides the two vowels together). Pratham: as now / glottal stop before the second vowel / a short
pause; two takes each (VITS varies). Own voice for reference.
Usage: .venv/bin/python round17.py -> out/r17/*.mp3, out/r17/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r17'
LENGTH = 1.15 / 0.875
TEXTS = [
    'So evamāha.',
    'Te evamāhaṁsu: evaṁ, bhante.',
    'Atha kho āyasmā ānando bhagavantaṁ etadavoca.',
    'Tatra kho bhagavā bhikkhū āmantesi.',
    'So ahaṁ, bhante, idāni evaṁ pajānāmi.',
]
V = 'ʌaeoiuɪʊ'
HIATUS = re.compile(rf'(?<=[{V}ː]) (?=ˈ?[{V}])')  # a space between a vowel and a vowel
VARIANTS = [
    ('a', 'как сейчас', lambda s: s),
    ('b', 'гортанная смычка перед второй гласной (ʔ)', lambda s: HIATUS.sub(' ʔ', s)),
    ('c', 'короткая пауза между словами', lambda s: HIATUS.sub(', ', s)),
]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
own = PiperVoice.load('models/pali_dg-medium.onnx')
os.makedirs(OUT, exist_ok=True)


def render(v, ipa, length, f):
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-b:a', '64k', f], input=audio.tobytes(), check=True)


phrases = []
for n, text in enumerate(TEXTS):
    base = tune(to_ipa(text, full_a=True))
    vs = []
    for vid, label, fn in VARIANTS:
        for take in (1, 2):
            f = f'p{n}.{vid}{take}.mp3'
            render(pratham, fn(base), LENGTH, f'{OUT}/{f}')
            vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': fn(base)})
    render(own, to_ipa(text, full_a=True), 1.0 / 0.875, f'{OUT}/p{n}.own.mp3')
    vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'p{n}.own.mp3', 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': base, 'script': '', 'variants': vs,
                    'note': '★ где стык слов (So evamāha, āyasmā ānando) звучит чисто, без «р»/«й» между гласными'})
    print(n, flush=True)
json.dump({'round': 'r17', 'sections': [{'id': 'hiatus', 'title': 'Гласная + гласная на стыке слов', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
