"""Recording script for the own voice: SC Pali sentences picked so every sound pair of Pali is covered,
rare ones several times, in about TARGET_MIN minutes of reading.

Greedy set cover over diphones (adjacent letters, word edges included), lazy evaluation: a segment's gain
only shrinks as units get covered. Order = pick order, so the most useful lines get recorded first and a
session stopped halfway still covers the most.
Usage: python3 build_script.py -> site/record/script.json
"""
import glob
import heapq
import json
import os
import re
from collections import Counter

from pali_ipa import TOKEN, normalize

ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms/sutta'
BOOKS = ['dn', 'mn', 'sn', 'an', 'kn/dhp', 'kn/snp', 'kn/ud', 'kn/iti', 'kn/thag', 'kn/thig', 'kn/kp']
TARGET_MIN = 100
WANT = 4  # a unit stops adding value after this many occurrences


def units(text):
    out = []
    for w in re.findall(r'[a-zāīūṭḍṅñṇḷṃ]+', normalize(text)):
        t = ['#'] + TOKEN.findall(w) + ['#']
        out += [a + '_' + b for a, b in zip(t, t[1:])]
    return out


def seconds(text):  # slow careful reading: ~0.22 s a syllable plus a breath
    return 0.6 + 0.22 * len(re.findall(r'[aāiīuūeo]', normalize(text)))


cands, seen = [], set()
for book in BOOKS:
    for f in sorted(glob.glob(f'{ROOT}/{book}/**/*.json', recursive=True)):
        for sid, text in json.load(open(f, encoding='utf-8')).items():
            text = text.strip()
            key = re.sub(r'[^a-zāīūṭḍṅñṇḷṃ]', '', normalize(text))
            words = re.findall(r'[a-zāīūṭḍṅñṇḷṃ]+', normalize(text))
            # Pali words end in a vowel or ṃ: this drops the odd English note left in the data
            if (':0.' in sid or key in seen or not 30 <= len(text) <= 180 or re.search(r'[0-9…]|\bpe\b', text)
                    or any(not re.search(r'[aāiīuūeoṃ]$', w) for w in words)):
                continue
            seen.add(key)
            cands.append((sid, text, Counter(units(text)), seconds(text)))

have = Counter()


def gain(c):
    return sum(min(n, max(0, WANT - have[u])) / (1 + have[u]) for u, n in c[2].items()) / c[3]


heap = [(-gain(c), i) for i, c in enumerate(cands)]
heapq.heapify(heap)
picked, total = [], 0.0
while heap and total < TARGET_MIN * 60:
    g, i = heapq.heappop(heap)
    fresh = gain(cands[i])
    if heap and fresh < -heap[0][0] - 1e-9:  # stale score: re-queue with the current one
        heapq.heappush(heap, (-fresh, i))
        continue
    sid, text, us, sec = cands[i]
    picked.append({'id': sid, 'text': text})
    have.update(us)
    total += sec

all_units = Counter()
for c in cands:
    all_units.update(c[2].keys())
missing = [u for u in all_units if not have[u]]
os.makedirs('site/record', exist_ok=True)
json.dump(picked, open('site/record/script.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(f'{len(picked)} lines, ~{total / 60:.0f} min, {len(have)} of {len(all_units)} diphones covered;'
      f' uncovered (rarest in corpus): {sorted(missing, key=lambda u: all_units[u])[:15]}')
assert units('Evaṁ me') == ['#_e', 'e_v', 'v_a', 'a_ṃ', 'ṃ_#', '#_m', 'm_e', 'e_#']
