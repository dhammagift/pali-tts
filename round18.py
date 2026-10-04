"""Round 18: 'passambhayaṁ' read as 'пасамбхам': the open-a rule (round 9) turns 'bhaya' into 'bʰaj…',
which the voice glides into one syllable and swallows 'ya'. Pratham: as now / no open a before j / jj /
both; two takes each. Own voice for reference.
Usage: .venv/bin/python round18.py -> out/r18/*.mp3, out/r18/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import PRATHAM_RULES, to_ipa, tune

OUT = 'out/r18'
LENGTH = 1.15 / 0.875
TEXTS = [
    'Passambhayaṁ kāyasaṅkhāraṁ assasissāmīti sikkhati.',
    'Abhippamodayaṁ cittaṁ assasissāmīti sikkhati.',
    'Samādahaṁ cittaṁ, vimocayaṁ cittaṁ passasissāmīti sikkhati.',
    'Ayaṁ kho, bhikkhave, dhammo.',
]
V = 'ʌaeoiuɪʊ'
OPEN_A = PRATHAM_RULES[3][0]  # round 9's rule: unstressed medial ʌ -> a


def no_open_before_j(text):
    # rebuild tune() without the open-a rule where the next consonant is j
    ipa = to_ipa(text, full_a=True)
    for i, (rx, rep) in enumerate(PRATHAM_RULES):
        if i == 3:
            ipa = re.sub(OPEN_A.pattern.replace('(?!c)', '(?![cj])'), rep, ipa)
        else:
            ipa = rx.sub(rep, ipa)
    from pali_ipa import MONO_HIATUS
    return MONO_HIATUS.sub(r'\1, ', ipa)


JJ = re.compile(rf'(?<=[{V}])j(?=[{V}ˈ])')
VARIANTS = [
    ('a', 'как сейчас', lambda t: tune(to_ipa(t, full_a=True))),
    ('b', 'без открытого «а» перед y', no_open_before_j),
    ('c', 'удвоенное y (jj)', lambda t: JJ.sub('jj', tune(to_ipa(t, full_a=True)))),
    ('d', 'без открытого «а» + jj', lambda t: JJ.sub('jj', no_open_before_j(t))),
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
    vs = []
    for vid, label, fn in VARIANTS:
        ipa = fn(text)
        for take in (1, 2):
            f = f'p{n}.{vid}{take}.mp3'
            render(pratham, ipa, LENGTH, f'{OUT}/{f}')
            vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': ipa})
    render(own, to_ipa(text, full_a=True), 1.0 / 0.875, f'{OUT}/p{n}.own.mp3')
    vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'p{n}.own.mp3', 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': VARIANTS[0][2](text), 'script': '', 'variants': vs,
                    'note': '★ где «-ayaṁ» (passambhayaṁ, vimocayaṁ) звучит полностью: «пассамбхаям», а не «пасамбхам»'})
    print(n, [fn(text)[:40] for _, _, fn in VARIANTS] if n == 0 else '', flush=True)
json.dump({'round': 'r18', 'sections': [{'id': 'aya', 'title': '-aya-: «пасамбхам»', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
