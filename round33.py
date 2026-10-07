"""Round 33: DN 22 — the owner heard kāyasamphassajaṁ from pratham as «кайя сасфассазян» (m lost, ph as f, j as z).
Variants of that word only, 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round33.py -> out/r33/; then build_page.py with ROUND = 'r33'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r33'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
TEXT = 'Yaṁ kho bhikkhave kāyikaṁ dukkhaṁ kāyikaṁ asātaṁ kāyasamphassajaṁ dukkhaṁ asātaṁ vedayitaṁ'
W = 'sʌmpʰˈʌssʌɟən'
V = [('a', 'как сейчас', W),
     ('b', 'j как дж', 'sʌmpʰˈʌssʌdʒən'),
     ('c', 'долгое m', 'sʌmːpʰˈʌssʌɟən'),
     ('d', 'ph как п+х', 'sʌmphˈʌssʌɟən'),
     ('e', 'долгое m + п+х + дж', 'sʌmːphˈʌssʌdʒən')]

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
    json.dump({'round': 'r33', 'sections': [{'id': 'p', 'title': 'kāyasamphassajaṁ, 0.7x', 'multi_best': False, 'phrases': [
        {'id': 'p0', 'text': TEXT, 'ipa': base, 'script': '', 'variants': vs, 'note': '★ где kāyasamphassajaṁ звучит правильно'}]}]},
        open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
