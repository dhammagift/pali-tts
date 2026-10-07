"""Round 35: vedayitaṁ read «ведайеиа» (round 33 comment; the owner wants veda-I-ta). y is doubled after a
(round 18 rule). Only this word varies; the rest of the DN 22 phrase as now (with round 33's mph). 0.7x, 2 takes.
Usage (on f3): .venv/bin/python round35.py -> out/r35/; then build_page.py with ROUND = 'r35'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR
from round33 import TEXT

OUT = 'out/r35'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
W = 'ʋˈeːdʌjjɪtən'
V = [('a', 'как сейчас (yy)', W),
     ('b', 'одно y', 'ʋˈeːdʌjɪtən'),
     ('c', 'одно y, ударение на i', 'ʋeːdʌjˈɪtən'),
     ('d', 'долгое i', 'ʋˈeːdʌjiːtən')]

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    base = tune(to_ipa(TEXT, full_a=True))
    assert W in base, base
    vs = []
    for vid, label, w in V:
        s = base.replace(W, w)
        for take in (1, 2):
            audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
            f = f'p0.{vid}{take}.mp3'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
    json.dump({'round': 'r35', 'sections': [{'id': 'p', 'title': 'vedayitaṁ, 0.7x', 'multi_best': False, 'phrases': [
        {'id': 'p0', 'text': TEXT, 'ipa': base, 'script': '', 'variants': vs, 'note': '★ где vedayitaṁ звучит правильно'}]}]},
        open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
