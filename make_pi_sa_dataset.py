"""Kaggle datasets for pi-sa-voice-train (owner 2026-10-23: «обучай санскритский, он звучит неприятно из-за тембра»):
pratham's timbre with a Sanskrit voice's pronunciation. Indic Parler-TTS (Aryan; round sa1: 4 of 5 ok) reads Pali
in Devanagari, kNN-VC turns it into pratham's timbre, Piper is fine-tuned from pratham on that.
- <OUT>/texts: texts.csv (name|Devanagari|ids: pratham's ids of plain to_ipa - no tune(), those fix pratham's Hindi
  habits, not a Sanskrit reader's), phonemes.json, ref/*.wav (pratham at 16 kHz: kNN-VC's matching set, made by the
  live service), pali_ipa.py for the samples. Sentences of the four nikāyas' root text, 30-160 characters, no …pe….
- <OUT>/parler: the gated model's files (Apache 2.0) from this machine's Hugging Face cache: Kaggle has no token.
Usage (on f3): .venv/bin/python make_pi_sa_dataset.py /root/pi-sa [n]
"""
import glob
import json
import os
import random
import re
import shutil
import sys

from piper import PiperVoice

from pali_ipa import to_ipa, to_script

OUT, N = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2400
ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms/sutta'
voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
segs = []
for book in ('dn', 'mn', 'sn', 'an'):
    for f in sorted(glob.glob(f'{ROOT}/{book}/**/*.json', recursive=True)):
        for k, t in json.load(open(f, encoding='utf-8')).items():
            t = t.strip()
            if ':0.' in k or not 30 <= len(t) <= 160 or 'pe…' in t or '…' in t or not re.search(r'[.?!”’;,]$', t):
                continue
            segs.append(t)
random.Random(2026).shuffle(segs)
T = f'{OUT}/texts'
os.makedirs(f'{T}/ref', exist_ok=True)
rows, seen = [], set()
for t in dict.fromkeys(segs):
    deva = re.sub(r'\.(?=\s|$|”|’)', '।', to_script(t, 'deva', final_m=False)).strip()
    ids = voice.phonemes_to_ids(list(to_ipa(t, full_a=True)))
    rows.append(f"s{len(rows):05d}.wav|{deva}|{' '.join(map(str, ids))}")
    if len(rows) == N:
        break
open(f'{T}/texts.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump(voice.config.phoneme_id_map, open(f'{T}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in glob.glob('/root/sa-test/ref/*.wav'):
    shutil.copy(f, f'{T}/ref/')
shutil.copy('pali_ipa.py', T)
json.dump({'title': 'pi-sa-texts', 'id': 'dhammagift/pi-sa-texts', 'licenses': [{'name': 'CC0-1.0'}]}, open(f'{T}/dataset-metadata.json', 'w'))
P = f'{OUT}/parler'
os.makedirs(P, exist_ok=True)
snap = glob.glob('/root/.cache/huggingface/hub/models--ai4bharat--indic-parler-tts/snapshots/*/')[0]
for f in os.listdir(snap):
    shutil.copy(os.path.join(snap, f), P)  # follows the cache's symlinks
json.dump({'title': 'indic-parler-tts-weights', 'id': 'dhammagift/indic-parler-tts-weights', 'licenses': [{'name': 'other'}]},
          open(f'{P}/dataset-metadata.json', 'w'))
print(len(rows), 'texts', sum(len(r.split('|')[1]) for r in rows), 'chars;', len(os.listdir(f'{T}/ref')), 'ref wavs')
