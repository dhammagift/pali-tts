"""Round 34: the owner says every j sounds bad from pratham (jā, jarā, ...). j/jh variants in all phrases, 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round34.py -> out/r34/; then build_page.py with ROUND = 'r34'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r34'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
TEXTS = ['Jātipi dukkhā, jarāpi dukkhā, maraṇampi dukkhaṁ.',
         'Yā tesaṁ tesaṁ sattānaṁ tamhi tamhi sattanikāye jāti sañjāti okkanti nibbatti.',
         'Kāyasamphassajaṁ dukkhaṁ asātaṁ vedayitaṁ.',
         'Ñāṇaṁ udapādi, paññā udapādi, vijjā udapādi, āloko udapādi.',
         'Vivicceva kāmehi paṭhamaṁ jhānaṁ upasampajja viharati.']
# pratham's training data was phonemized by espeak hi, where ज is dʒ; ɟ is ours (rounds 1-5)
V = [('a', 'как сейчас (ɟ)', lambda s: s),
     ('b', 'дж (dʒ)', lambda s: s.replace('ɟ', 'dʒ')),
     ('c', 'дь (dʲ)', lambda s: s.replace('ɟ', 'dʲ'))]

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        base = tune(to_ipa(text, full_a=True))
        assert 'ɟ' in base, base
        vs = []
        for vid, label, fn in V:
            s = fn(base)
            for take in (1, 2):
                audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
                f = f'p{i}.{vid}{take}.mp3'
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
                vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
        phrases.append({'id': f'p{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': '★ где j звучит правильно'})
    json.dump({'round': 'r34', 'sections': [{'id': 'p', 'title': 'j / jh, 0.7x', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
