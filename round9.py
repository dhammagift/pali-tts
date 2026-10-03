"""Round 9: medial short a dropped by Hindi schwa syncope (viharati -> "viharti") for Piper pratham on top of the round-4 rules (pali_ipa.tune).

Each phrase changes one thing in our IPA: single ñ, ññ, word-final ṁ, tempo.
Usage: .venv/bin/python round4.py  -> out/r9/*.mp3, out/r9/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import PRATHAM_RULES, to_ipa, tune

OUT = 'out/r9'
v = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
END = r'(?=[ ,.?!]|$)'


def render(path, ipa, length=1.15):
    if os.path.exists(path):
        return
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)),
                                   SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-b:a', '64k', path], input=audio.astype(np.float32).tobytes(), check=True)


def phrase(pid, text, note, variants):
    """variants: (id, label, ipa transform, length_scale)."""
    base = tune(to_ipa(text, full_a=True))
    vs = []
    for vid, label, fn, length in variants:
        ipa = fn(base)
        f = f'{OUT}/{pid}.{vid}.mp3'
        render(f, ipa, length)
        vs.append({'id': vid, 'label': label, 'file': os.path.basename(f), 'sent': ipa})
    print(pid)
    return {'id': pid, 'text': text, 'note': note, 'ipa': base, 'script': '', 'variants': vs}


V = 'ʌaeoiuɪʊ'
# unstressed short a between consonants with a vowel after: where Hindi drops it (vi-ha-ra-ti -> vihar-ti)
MEDIAL_A = re.compile(rf'(?<!ˈ)ʌ(?=[^\s{V}ˈ,.?!]+ˈ?[{V}])')
os.makedirs(OUT, exist_ok=True)
items = [
    phrase('sy', 'Ekaṁ samayaṁ bhagavā sāvatthiyaṁ viharati. Bhagavato, karoti, bhavati, upasaṅkamati, pabbajitena.',
           'краткое a посередине слова: ★ где «вихарати», а не «вихарти»',
           [(k, label, fn, 1.15) for k, label, fn in [
               ('a', 'как сейчас (ʌ)', lambda s: s),
               ('b', 'побочное ударение ˌ на этом a', lambda s: MEDIAL_A.sub('ˌʌ', s)),
               ('c', 'открытое a', lambda s: MEDIAL_A.sub('a', s)),
               ('d', 'ɐ', lambda s: MEDIAL_A.sub('ɐ', s))]]),
]
json.dump({'round': 'r9', 'sections': [{'id': 'piper', 'title': 'Piper pratham: свои правила', 'multi_best': False,
                                        'phrases': items}]},
          open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
