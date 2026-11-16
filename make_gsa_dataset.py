"""Data for pratham with Google's pronunciation (owner 2026-11-16, round gsa1: Google in pratham's timbre «намного лучше»):
the same 2400 sentences as make_pi_sa_dataset.py (four nikāyas' root text, 30-160 characters, no …pe…), now for
Google's Sanskrit TTS (gtts/): gtts/lines.tsv (id<TAB>Devanagari, our r73 comma between ā and a written in) and
<OUT>/texts.csv (name|Devanagari|pratham's ids of to_ipa with today's rules), phonemes.json, ref/ (kNN-VC's set).
Usage (on f3): .venv/bin/python make_gsa_dataset.py /root/gsa [n]
"""
import glob
import json
import os
import random
import re
import shutil
import sys

from piper import PiperVoice

from pali_ipa import to_ipa
from round_gsa1 import google_text

OUT, N = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2400
ROOT = os.environ.get('PLI_ROOT', '/root/sherpa-pi/canon/sutta')
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
rows, lines = [], []
for t in dict.fromkeys(segs):
    name = f's{len(rows):05d}'
    deva = re.sub(r'\.(?=\s|$|”|’)', '।', google_text(t)).strip()
    rows.append(f"{name}.wav|{deva}|{' '.join(map(str, voice.phonemes_to_ids(list(to_ipa(t, full_a=True)))))}")
    lines.append(f'{name}\t{deva}\n')
    if len(rows) == N:
        break
open(f'{T}/texts.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
open('gtts/lines.tsv', 'w', encoding='utf-8').write(''.join(lines))
json.dump(voice.config.phoneme_id_map, open(f'{T}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in glob.glob('/root/pi-sa/texts/ref/*.wav'):
    shutil.copy(f, f'{T}/ref/')
shutil.copy('pali_ipa.py', T)
print(len(rows), 'texts', sum(len(r.split('|')[1]) for r in rows), 'chars;', len(os.listdir(f'{T}/ref')), 'ref wavs')
