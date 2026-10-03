"""Round 12: which c-fix is stable? VITS samples noise on every call, so each variant gets 3 takes
at the reader's default pace (Pali 0.7 -> length_scale 1.15 / 0.875).

Usage: .venv/bin/python round12.py -> out/r12/*.mp3, out/r12/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r12'
TEXT = 'Dhammacakkappavattanasutta. Ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati. Paccattaṁ veditabbo viññūhi.'
LENGTH = 1.15 / 0.875
V = 'ʌaeoiuɪʊː'
voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
base = tune(to_ipa(TEXT, full_a=True))
VARIANTS = [
    ('a', 'как сейчас (ʌ перед c)', base, 0.6),
    ('b', 'ʌ перед c + удвоенное cc', re.sub(rf'(?<=[{V}])c(?=[{V}ˈ])', 'cc', base), 0.6),
    ('c', 'граница слова перед c', re.sub(rf'(?<=[{V}])c(?=[{V}ˈ])', ' c', base), 0.6),
    ('d', 'как сейчас, меньше шума модели (0.33)', base, 0.333),
]
os.makedirs(OUT, exist_ok=True)
phrases = []
for take in (1, 2, 3):
    vs = []
    for vid, label, ipa, noise in VARIANTS:
        f = f'{OUT}/t{take}.{vid}.mp3'
        audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)),
                                           SynthesisConfig(length_scale=LENGTH, noise_scale=noise, noise_w_scale=0.7))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                        '-b:a', '64k', f], input=audio.astype(np.float32).tobytes(), check=True)
        vs.append({'id': vid, 'label': f'{label} · дубль {take}', 'file': os.path.basename(f), 'sent': ipa})
    phrases.append({'id': f't{take}', 'text': TEXT, 'note': f'Дубль {take} из 3: ★ где «dhammaчakka», ✗ где «щ»',
                    'ipa': base, 'script': '', 'variants': vs})
json.dump({'round': 'r12', 'sections': [{'id': 'c', 'title': 'Звук c: стабильность (3 дубля)', 'multi_best': True,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print([v[2][:30] for v in VARIANTS])
