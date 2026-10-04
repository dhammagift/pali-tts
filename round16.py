"""Round 16: Pali words inside English translations. Now: respelled for espeak (Dhamma -> "Damma" -> "dæmə",
sutta untouched -> "sʌɾə"). New: our own phonemes for the Pali words (en_phonemes). Three English voices, blind.
Usage: .venv/bin/python round16.py -> out/r16/*.mp3, out/r16/index.json
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from respell import en_phonemes, respell

OUT = 'out/r16'
TEXTS = [
    'This is the sutta on the Dhamma, the Blessed One taught the bhikkhus.',
    'At one time the Buddha was staying near Vārāṇasī, in the deer park at Isipatana.',
    'Then Venerable Sāriputta and Venerable Ānanda went up to the Tathāgata.',
    'The noble eightfold path leads to Nibbāna; the first jhāna is free of sensual pleasures.',
]
VOICES = ['alan', 'norman', 'kathleen']
MODELS = {'alan': 'en_GB-alan-medium', 'norman': 'en_US-norman-medium', 'kathleen': 'en_US-kathleen-low'}
os.makedirs(OUT, exist_ok=True)
phrases = []
loaded = {v: PiperVoice.load(f'models/{MODELS[v]}.onnx') for v in VOICES}
for n, text in enumerate(TEXTS):
    vs = []
    for vid in VOICES:
        v = loaded[vid]
        for kind, label in (('old', 'как сейчас'), ('new', 'новое: свои фонемы для пали')):
            ph = [p for s in v.phonemize(respell(text, 'en')) for p in s] if kind == 'old' else en_phonemes(v, text)
            audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(ph), SynthesisConfig(noise_scale=0.6, noise_w_scale=0.7))
            f = f'{OUT}/p{n}.{vid}.{kind}.mp3'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(v.config.sample_rate), '-ac', '1',
                            '-i', '-', '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-b:a', '64k', f],
                           input=audio.astype(np.float32).tobytes(), check=True)
            vs.append({'id': f'{vid}.{kind}', 'label': f'{vid}: {label}', 'file': os.path.basename(f), 'sent': ''.join(ph)})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                    'note': '★ где слова пали (sutta, Dhamma, bhikkhu, имена) звучат правильно; нажмите на слово, которое читается неверно'})
    print(n, flush=True)
json.dump({'round': 'r16', 'sections': [{'id': 'en', 'title': 'Пали в английском переводе', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
