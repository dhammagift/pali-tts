"""Round 6: word-final ṁ only for Piper pratham on top of the round-4 rules (pali_ipa.tune).

Each phrase changes one thing in our IPA: single ñ, ññ, word-final ṁ, tempo.
Usage: .venv/bin/python round4.py  -> out/r6/*.mp3, out/r6/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r6'
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


FINAL_NG = r'([ʌaɪiʊueo])(ː?)ŋː(?=[ ,.?!]|$)'
os.makedirs(OUT, exist_ok=True)
items = [
    phrase('ng', 'Evaṁ me sutaṁ. Paṭhamaṁ jhānaṁ upasampajja viharati. Seyyathidaṁ, sammādiṭṭhi. Idaṁ dukkhaṁ ariyasaccaṁ.',
           'конечное ṁ: ★ где «evaṁ», «sutaṁ», «jhānaṁ» звучат правильно',
           [(k, label, fn, 1.15) for k, label, fn in [
               ('a', 'ṁ как носовой долгий гласный, без согласной', lambda s: re.sub(FINAL_NG, '\\1\u0303ː', s)),
               ('b', 'ṁ как m', lambda s: re.sub(FINAL_NG, '\\1\\2m', s)),
               ('c', 'ṁ как ɴ (заднее носовое)', lambda s: re.sub(FINAL_NG, '\\1\\2ɴ', s)),
               ('d', 'ṁ как n', lambda s: re.sub(FINAL_NG, '\\1\\2n', s))]]),
]
json.dump({'round': 'r6', 'sections': [{'id': 'piper', 'title': 'Piper pratham: свои правила', 'multi_best': False,
                                        'phrases': items}]},
          open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
