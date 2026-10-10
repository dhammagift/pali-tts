"""Two-speaker Kaggle dataset: pratham's timbre and quality, the owner's Pali pronunciation (owner, 2026-10-10: «переучить
читать, но оставить и тембр и качество»; converting the owner's voice to pratham's timbre with kNN-VC was much worse).
- speaker 'pratham': pratham reads DN + MN sentences with our rules (tune(to_ipa)) - ids are what it was fed;
- speaker 'owner': the owner's 2 h (data/kaggle, the dg voice's data) with plain to_ipa - ṁ stays ŋ, ṭṭh stays ʈʈʰ,
  symbols pratham's half never has, so the model learns them from the owner only.
A model trained from rohan on both then reads speaker pratham with the owner's symbols where pratham fails.
Ids use rohan's map (the warm start); pratham's map is the same minus 4 symbols.
Usage (f3): .venv/bin/python make_pi_mix_dataset.py data/kaggle /root/vc/sc /root/pimix 3.5
"""
import json
import glob
import os
import random
import shutil
import sys
import wave

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OWNER, SC, OUT, HOURS = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
rohan = PiperVoice.load('models/hi_IN-rohan-medium.onnx')
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
CFG = SynthesisConfig(length_scale=1.15, noise_scale=0.6, noise_w_scale=0.7)  # the site's pace at 0.8
os.makedirs(f'{OUT}/wavs', exist_ok=True)
rows = []
for line in open(f'{OWNER}/metadata.csv', encoding='utf-8'):
    if line.strip():
        name, text, ids = line.rstrip('\n').split('|')
        shutil.copy(f'{OWNER}/wavs/{name}', f'{OUT}/wavs/{name}')
        rows.append(f'{name}|owner|{text}|{ids}')
owner_rows = len(rows)
segs = []
for f in sorted(glob.glob(f'{SC}/*.json')):
    segs += [t.strip() for t in json.load(open(f, encoding='utf-8')).values() if 30 <= len(t.strip()) <= 180]
random.Random(5).shuffle(segs)
total = 0.0
for i, text in enumerate(segs):
    if total >= HOURS * 3600:
        break
    name = f'pr_{i:05d}.wav'
    ipa = tune(to_ipa(text, full_a=True))
    if not os.path.exists(f'{OUT}/wavs/{name}'):
        audio = pratham.phoneme_ids_to_audio(pratham.phonemes_to_ids(list(ipa)), CFG)
        with wave.open(f'{OUT}/wavs/{name}', 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype('int16').tobytes())
    with wave.open(f'{OUT}/wavs/{name}') as w:
        total += w.getnframes() / 22050
    rows.append(f"{name}|pratham|{text}|{' '.join(map(str, rohan.phonemes_to_ids(list(ipa))))}")
    if i % 200 == 199:
        print(i + 1, f'{total / 3600:.2f} h', flush=True)
open(f'{OUT}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump(rohan.config.phoneme_id_map, open(f'{OUT}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in ('pali_ipa.py',):
    shutil.copy(f, f'{OUT}/{f}')
json.dump({'title': 'pali-mix-voice-data', 'id': 'dhammagift/pali-mix-voice-data', 'licenses': [{'name': 'CC-BY-NC-SA-4.0'}]},
          open(f'{OUT}/dataset-metadata.json', 'w'))
print(owner_rows, 'owner clips,', len(rows) - owner_rows, f'pratham clips ({total / 3600:.2f} h)')
