"""Round 11: word-internal c after a vowel turns into "shch" (dhammacakka) while word-initial c is fine for Piper pratham on top of the round-4 rules (pali_ipa.tune).

Each phrase changes one thing in our IPA: single ñ, ññ, word-final ṁ, tempo.
Usage: .venv/bin/python round4.py  -> out/r11/*.mp3, out/r11/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import PRATHAM_RULES, to_ipa, tune

OUT = 'out/r11'
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


os.makedirs(OUT, exist_ok=True)
V = 'ʌaeoiuɪʊː'
MID_C = re.compile(rf'(?<=[{V}])c(?=[c{V}ˈ])')  # c right after a vowel inside a word
items = [
    phrase('c', 'Dhammacakkappavattanasutta. Paccattaṁ veditabbo viññūhi. Vicikicchā, sacca, vacī, pacchā.',
           'c внутри слова после гласной (dhammacakka, paccattaṁ, vicikicchā, sacca): ★ где «ч», как в начале слова (cakkhuṁ)',
           [(k, label, fn, 1.15) for k, label, fn in [
               ('a', 'как сейчас', lambda s: s),
               ('b', 'c удвоено (cc)', lambda s: MID_C.sub('cc', s).replace('ccc', 'cc')),
               ('c', 'перед c гласная ʌ, а не открытое a', lambda s: re.sub(r'a(?=c)', 'ʌ', s)),
               ('d', 'граница слова перед одиночным c (как «dhamma cakka»)', lambda s: re.sub(rf'(?<=[{V}])c(?=[{V}ˈ])', ' c', s))]]),
]
json.dump({'round': 'r11', 'sections': [{'id': 'piper', 'title': 'Piper pratham: свои правила', 'multi_best': False,
                                        'phrases': items}]},
          open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
