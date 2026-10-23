"""ru_yo.tsv: words of DG's Russian texts printed with е where ё is meant (owner 2026-10-23: «ненадежны» read
ненаде́жны; «все где пропущено ё»). The safe half of the eyo-kernel dictionary (github.com/e2yo/eyo-kernel,
dictionary/safe.txt, MIT, (c) Denis Seleznev: words that always have ё; its not_safe half - все/всё, небо/нёбо - is
left out), kept to the word forms that occur in DG's Russian texts, so the offline data stays small.
respell.py adds them to RU_ACCENT (the same table on the service and offline).
Usage: python3 build_ru_yo.py [dg.db] -> ru_yo.tsv
"""
import re
import sqlite3
import sys
import urllib.request

DB = sys.argv[1] if len(sys.argv) > 1 else '/var/www/dg-node-test/dg.db'
SAFE = 'https://raw.githubusercontent.com/e2yo/eyo-kernel/master/dictionary/safe.txt'
words = {w for (t,) in sqlite3.connect(DB).execute("select txt from texts where lang = 'ru'") for w in re.findall('[а-яё]+', t.lower())}
yo = {}
for line in urllib.request.urlopen(SAFE).read().decode('utf-8').split('\n'):
    w = line.split('#')[0].strip()
    if not w or w.startswith('_'):  # _word: only in lower case, a name's homonym (_киёв): not ours to guess
        continue
    for f in ([w] if '(' not in w else [w.split('(')[0] + p for p in re.split(r'[(|)]', w)[1:-1]]):
        yo[f.lower().replace('ё', 'е')] = f.lower()
rows = sorted((e, y) for e, y in yo.items() if e in words and e != y)
open('ru_yo.tsv', 'w', encoding='utf-8').write(''.join(f'{e}\t{y}\n' for e, y in rows))
print(len(rows), 'words')
