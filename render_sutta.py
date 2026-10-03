"""Render a whole sutta: Piper (our IPA) and Google (voice.js pipeline), segment by segment with pauses.

Usage: .venv/bin/python render_sutta.py sn56.11  -> out/sutta/<id>.{pratham,google}.mp3
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms/sutta/'
SR = 22050
sid = sys.argv[1]
path = glob.glob(f'{ROOT}**/{sid}_root-pli-ms.json', recursive=True)[0]
segs = [(k, v.strip()) for k, v in json.load(open(path, encoding='utf-8')).items()
        if v.strip() and not any(c.isdigit() for c in v)]  # drop "Saṁyutta Nikāya 56.11"-style headers
os.makedirs('out/sutta', exist_ok=True)


def pause(text):
    return np.zeros(int(SR * (0.8 if text.rstrip('”’').endswith(('.', '?', '!')) else 0.4)), dtype=np.float32)


def write(pcm, dst):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                    '-b:a', '96k', dst], input=pcm.astype(np.float32).tobytes(), check=True)


# Piper pratham, our IPA (full short a, stress) + pratham's own listening-test rules (ñ, ññ, final ṁ)
v = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
cfg = SynthesisConfig(length_scale=1.15, noise_scale=0.6, noise_w_scale=0.7)
parts = []
for _, text in segs:
    parts += [v.phoneme_ids_to_audio(v.phonemes_to_ids(list(tune(to_ipa(text, full_a=True)))), cfg), pause(text)]
write(np.concatenate(parts), f'out/sutta/{sid}.pratham_tuned.mp3')

# Google pa-IN with the live voice.js rules
gdir = f'out/sutta/{sid}.google'
json.dump(segs, open(f'{gdir}.json', 'w', encoding='utf-8'), ensure_ascii=False)
subprocess.run(['node', 'google_segments.js', f'{gdir}.json', gdir], check=True)
parts = []
for i, (_, text) in enumerate(segs):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', f'{gdir}/{i:03d}.mp3', '-ac', '1', '-ar', str(SR),
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    parts += [np.frombuffer(raw, dtype=np.float32), pause(text)]
write(np.concatenate(parts), f'out/sutta/{sid}.google.mp3')

