"""Round gsa1 (owner 2026-11-16: «произношение как у Google, тембр pratham»): Google's Sanskrit TTS (sa-IN, Android 16
in GitHub Actions, gtts/) reads Pali in Devanagari, slowed by the engine itself to pratham's pace at 0.7x (speech rate
0.63: 3 smoke lines were 4.6/3.3/8.3 s against pratham's 7.7/4.9/13.1), kNN-VC turns it into pratham's timbre
(Kaggle gtts-vc-smoke) - against pratham as in DG (0.7x). el2's 16 lines, the ones the old rounds kept failing on. Blind.
Usage (on f3): .venv/bin/python round_gsa1.py lines       -> gtts/lines.tsv (then the gtts workflow)
               .venv/bin/python round_gsa1.py build <dir> -> out/gsa1/ from kNN-VC's p00.wav...; then build_page.py
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request

from pali_ipa import to_script
from round_el2 import TEXTS

OUT = 'out/gsa1'


def pratham(text):  # as round_pisa1's (which reads sys.argv on import): the live service, DG's pace
    r = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': 'pratham', 'rate': 0.7}).encode(),
                               {'Content-Type': 'application/json'})
    return base64.b64decode(json.loads(urllib.request.urlopen(r, timeout=300).read())['audioContent'])


def google_text(text):
    # our r73 in the text: a comma between a word-final ā and a word starting with a (Google reads sutavā ariya as one word too)
    # quotes out: to_script turns them into commas (“Iti → ,इति; bhaveyyā’ti → भवेय्या,ति), and ’ti is one word with what it follows
    return to_script(re.sub(r'ā (?=[aA])', 'ā, ', re.sub('[“”‘’"]', '', text)))


if sys.argv[1] == 'lines':
    open('gtts/lines.tsv', 'w', encoding='utf-8').write(''.join(f'p{i:02d}\t{google_text(t)}\n' for i, (t, _) in enumerate(TEXTS)))
elif sys.argv[1] == 'build':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, (text, why) in enumerate(TEXTS):
        vs = []
        open(f'{OUT}/p{i:02d}.pratham.mp3', 'wb').write(pratham(text))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f'{sys.argv[2]}/p{i:02d}.wav', '-q:a', '7', f'{OUT}/p{i:02d}.google_vc.mp3'], check=True)
        for name in ('pratham', 'google_vc'):
            vs.append({'id': name, 'label': name, 'file': f'p{i:02d}.{name}.mp3', 'sent': ''})
        phrases.append({'id': f'p{i:02d}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'Было: {why}. ★ лучший; ✓ правильно; ✗ неправильно. На слово с ошибкой можно нажать'})
    json.dump({'round': 'gsa1', 'title': 'Выговор Google в тембре pratham',
               'intro': 'Выговор Google (санскритский голос, замедлен до темпа сайта) в тембре pratham против pratham, '
                        'как сейчас в DG (0.7x). Фразы — те, на которых спотыкались старые раунды. Вслепую.',
               'sections': [{'id': 'p', 'title': 'Пали: нерешённые места', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
