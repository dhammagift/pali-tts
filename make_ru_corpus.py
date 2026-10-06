"""Russian sentences for a synthetic voice dataset: from DG's Russian translations (the owner's own and the ones he
edited), one sentence per line, 30-180 chars, plain Cyrillic text (no digits, brackets, Latin), shuffled.
Usage (on f3): python3 make_ru_corpus.py /var/www/dg-node-prod/dg.db 3000 > kaggle-clone-gen/data/sentences.txt
"""
import random
import re
import sqlite3
import sys

TRANSLATORS = ('o', 'sv+edited+o', 'syrkin+edited+o', 'narinyanievmenenko+edited+o', 'kheminda+edited+o',
               'khemanando+edited+o', 'toporov+edited+o', 'shapovalov+edited+o', 'alokananda+edited+o')
SENT = re.compile(r'(?<=[.!?])\s+')
GOOD = re.compile(r'^[А-Яа-яЁё][А-Яа-яЁё ,.!?;:—–\-«»"]+$')

db, n = sys.argv[1], int(sys.argv[2])
con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
seen, out = set(), []
for (txt,) in con.execute(f"select txt from texts where lang='ru' and kind='translation' and translator in "
                          f"({','.join('?' * len(TRANSLATORS))})", TRANSLATORS):
    for s in SENT.split(re.sub(r'\s+', ' ', txt or '').strip()):
        s = s.strip(' "«»—–-')
        if 30 <= len(s) <= 180 and GOOD.match(s) and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
random.Random(1).shuffle(out)
print('\n'.join(out[:n]))
print(len(out), 'candidates', file=sys.stderr)
