"""Round 32b: round 32 played too fast for the owner to judge (it was the site's 1.0x). The variants he rated ok
(b full a, c stress on ra, d stress on haṁ) again at 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round32b.py -> out/r32b/; then build_page.py with ROUND = 'r32b'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR
from round32 import TEXT, V

OUT = 'out/r32b'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    base = tune(to_ipa(TEXT, full_a=True))
    vs = []
    for vid, label, fn in V:
        if vid == 'a':
            continue  # bad in both takes of round 32
        s = fn(base)
        for take in (1, 2):
            audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
            f = f'p0.{vid}{take}.mp3'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            vs.append({'id': f'{vid}{take}', 'label': f'{label} · 0.7x · дубль {take}', 'file': f, 'sent': s})
    json.dump({'round': 'r32b', 'sections': [{'id': 'p', 'title': 'arahaṁ, 0.7x', 'multi_best': False, 'phrases': [
        {'id': 'p0', 'text': TEXT, 'ipa': base, 'script': '', 'variants': vs, 'note': '★ где arahaṁ звучит правильно'}]}]},
        open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
