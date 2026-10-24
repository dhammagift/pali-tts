"""Kaggle job: where do DG's Russian voices put the stress wrong? (owner 2026-10-24: «почему ты нашёл только когда я
нашёл? можешь сам превентивно найти?»). RUAccent (MIT, github.com/Den4ikAI/ruaccent: dictionary + homograph model,
restores ё) stresses every unique Russian segment of DG (dataset dg-ru-segments: count<TAB>text). Output word_stress.json:
word (lower, as printed) -> {stressed form ('+' before the stressed vowel, ё where meant): occurrences}. Our side
(audit_ru_stress.py) compares that with the stress our phonemes give each word.
SMOKE=1: 2000 segments.
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys
import time

INPUT = os.environ.get('INPUT', '/kaggle/input')
SMOKE = os.environ.get('SMOKE', '0') == '1'
W = os.environ.get('WORK', '/kaggle/working')
SEGS = glob.glob(f'{INPUT}/**/segments.tsv', recursive=True)[0]

subprocess.run('pip install -q ruaccent', shell=True, check=True)  # CPU: Kaggle CPU sessions are free (owner: keep the GPU quota)
from ruaccent import RUAccent  # noqa: E402

acc = RUAccent()
acc.load(omograph_model_size='turbo3.1', use_dictionary=True, tiny_mode=False, device='CPU', workdir=f'{W}/ruaccent')
rows = [line.rstrip('\n').split('\t', 1) for line in open(SEGS, encoding='utf-8')]
rows = rows[:2000] if SMOKE else rows
stats = collections.defaultdict(collections.Counter)
t0 = time.time()
for k, (n, text) in enumerate(rows):
    try:
        out = acc.process_all(text)
    except Exception as e:  # noqa: BLE001 - one odd segment must not stop the run
        print('skip', k, e, flush=True)
        continue
    for w in re.findall(r'[А-Яа-яЁё+\-]+', out):
        plain = w.replace('+', '').replace('ё', 'е').replace('Ё', 'Е').lower()
        if '+' in w and re.fullmatch('[а-я-]+', plain):
            stats[plain][w.lower()] += int(n)
    if k % 5000 == 0:
        print(k, 'of', len(rows), round((time.time() - t0) / 60, 1), 'min', flush=True)
os.makedirs(f'{W}/out', exist_ok=True)
json.dump({w: dict(c) for w, c in stats.items()}, open(f'{W}/out/word_stress.json', 'w', encoding='utf-8'), ensure_ascii=False)
subprocess.run(f'rm -rf {W}/ruaccent', shell=True)
print('done', len(stats), 'words', round((time.time() - t0) / 60, 1), 'min')
sys.exit(0)
