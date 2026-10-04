"""Round 14: stress rule. Current (penult if heavy, else antepenult) vs heavy_back (a light antepenult
yields to the nearest heavy syllable before it: pītisukhaṁ -> PĪtisukhaṁ). Pratham and own voice e179, blind.
Usage: .venv/bin/python round14.py -> out/r14/*.mp3, out/r14/index.json
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r14'
EXP = 'out/export/out'
TEXTS = [
    'Vivekajaṁ pītisukhaṁ paṭhamaṁ jhānaṁ upasampajja viharati.',
    'Seyyathidaṁ, sammādiṭṭhi sammāsaṅkappo. Kaṁsi tvaṁ, bhikkhu, uddissa pabbajito?',
    'Ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati. Etarahi brahmacariyaṁ carati.',
    'So evaṁ samāhite citte parisuddhe pubbenivāsānussatiñāṇāya cittaṁ abhinīharati abhininnāmeti.',
]
VOICES = [('pratham', 'Piper pratham', 'models/hi_IN-pratham-medium.onnx', None, 1.15 / 0.875),
          ('own', 'свой голос e179', f'{EXP}/pali_dg-e179.onnx', f'{EXP}/pali_dg-medium.onnx.json', 1.0)]
os.makedirs(OUT, exist_ok=True)
phrases = []
for n, text in enumerate(TEXTS):
    vs = []
    for vid, vlabel, model, cfgp, length in VOICES:
        v = PiperVoice.load(model, config_path=cfgp)
        for hb, hlabel in ((False, 'ударение как сейчас'), (True, 'новое ударение (на тяжёлый слог)')):
            parts = []
            for sent in [s for s in text.replace('. ', '.\n').replace('? ', '?\n').split('\n') if s]:
                ipa = to_ipa(sent, full_a=True, heavy_back=hb)
                ipa = tune(ipa) if vid == 'pratham' else ipa
                parts += [v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)),
                                                 SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7)),
                          np.zeros(8000, dtype=np.float32)]
            f = f'{OUT}/p{n}.{vid}.{int(hb)}.mp3'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                            '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-b:a', '64k', f],
                           input=np.concatenate(parts).tobytes(), check=True)
            vs.append({'id': f'{vid}.{int(hb)}', 'label': f'{vlabel}: {hlabel}', 'file': os.path.basename(f), 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'note': '★ где ударения естественнее; нажмите на слово с неверным ударением',
                    'ipa': to_ipa(text, full_a=True, heavy_back=True), 'script': '', 'variants': vs})
    print(n, flush=True)
json.dump({'round': 'r14', 'sections': [{'id': 'stress', 'title': 'Ударение', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
