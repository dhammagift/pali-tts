"""Round 36: only the j of kāyasamphassajaṁ (between vowels) - still wrong in round 35, where ph (round 33) and
vedayitaṁ (round 35) were already ok. Like the single c between vowels (round 12: doubled cc was right every time).
Two phrases: the two words, and kāyasamphassajaṁ alone. 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round36.py -> out/r36/; then build_page.py with ROUND = 'r36'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r36'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
TEXTS = ['Kāyasamphassajaṁ vedayitaṁ.', 'Kāyasamphassajaṁ.']
W = 'ʌɟən'
V = [('a', 'как сейчас (j)', W),
     ('b', 'jj', 'ʌɟɟən'),
     ('c', 'долгое j', 'ʌɟːən')]

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        base = tune(to_ipa(text, full_a=True))
        assert base.count(W) == 1, base
        vs = []
        for vid, label, w in V:
            s = base.replace(W, w)
            for take in (1, 2):
                audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
                f = f'p{i}.{vid}{take}.mp3'
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
                vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
        phrases.append({'id': f'p{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': '★ где j в -ssajaṁ правильная'})
    json.dump({'round': 'r36', 'sections': [{'id': 'p', 'title': 'j в kāyasamphassajaṁ, 0.7x', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
