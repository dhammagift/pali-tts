"""Texts for Miles's voice v3 (owner 2026-10-23, «а почему майлса голос так не делали?»): his 300 takes are ~20 min, too
little for Piper; ryan reads a few hours of sutta English, kNN-VC turns it into Miles's timbre (kaggle-en-miles-vc).
Sentences of Sujato's translations (CC0) from DN, MN, SN, AN, 40-220 characters, one per segment, shuffled with a fixed
seed; phoneme ids as tts_server gives an English voice (respell.en_phonemes, ids from ryan's map).
Usage (on f3): SC_TR=/root/sc-translation .venv/bin/python make_en_miles_vc_texts.py /root/en-miles/vctexts [n]
"""
import glob
import json
import os
import random
import re
import sys

from piper import PiperVoice

from respell import en_expand, en_phonemes

OUT, N = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2600
TR = os.environ.get('SC_TR', '/root/sc-translation')
voice = PiperVoice.load('models/en_US-ryan-medium.onnx')
segs = []
for book in ('dn', 'mn', 'sn', 'an'):
    for f in sorted(glob.glob(f'{TR}/en/sujato/sutta/{book}/**/*.json', recursive=True)):
        for k, t in json.load(open(f, encoding='utf-8')).items():
            t = t.strip()
            # a whole sentence of ordinary prose: no headings (k ends in :0.x), no ellipses of repeated text
            if ':0.' in k or not 40 <= len(t) <= 220 or '…' in t or not re.search(r'[.?!”’]$', t):
                continue
            segs.append(t)
random.Random(2026).shuffle(segs)
os.makedirs(OUT, exist_ok=True)
rows, seen = [], set()
for t in segs:
    if t in seen:
        continue
    seen.add(t)
    ids = voice.phonemes_to_ids(en_phonemes(voice, en_expand(t)))
    rows.append(f"v{len(rows):05d}.wav|{t}|{' '.join(map(str, ids))}")
    if len(rows) == N:
        break
open(f'{OUT}/texts.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump({'title': 'en-miles-vc-texts', 'id': 'dhammagift/en-miles-vc-texts', 'licenses': [{'name': 'CC0-1.0'}]},
          open(f'{OUT}/dataset-metadata.json', 'w'))
print(len(rows), 'texts', sum(len(r.split('|')[1]) for r in rows), 'chars')
