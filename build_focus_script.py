"""Recording script for the sounds the voices get wrong (owner, 2026-10-10: «давай я хотя бы какие-то сэмплы запишу»;
the pmix round: ṁ bad in every voice, ṭṭh better only after retraining). Short lines from the Pātimokkha and the suttas,
picked greedily for word-final ṁ (-aṁ -iṁ -uṁ, after t/tt too), ṭṭh, ṇh, ññ and the words the owner named as misread;
each kind of case counts less the more often it is already in. These lines go first in site/record/script.json, the old
(diphone) script after them, so the record page asks for them first.
Usage: python3 build_focus_script.py [n_lines]
"""
import glob
import json
import re
import sys
from collections import Counter

from pali_ipa import normalize

ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms'
SOURCES = [f'{ROOT}/vinaya/pli-tv-bu-pm_root-pli-ms.json', f'{ROOT}/vinaya/pli-tv-bi-pm_root-pli-ms.json'] + \
    sorted(glob.glob(f'{ROOT}/sutta/dn/**/*.json', recursive=True)) + sorted(glob.glob(f'{ROOT}/sutta/mn/**/*.json', recursive=True))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
# the owner's misread words (rounds 46-54, Pātimokkha lists #1-#3): each wanted at least once
NAMED = ['kātuṃ', 'tikkhattuṃ', 'paggayha', 'asaṃvāso', 'taṇṭhāna', 'hemanta', 'tuṇhī', 'uddiṭṭhaṃ', 'niṭṭhite', 'dhārayāmīti',
         'pucchāmi', 'sammutiyā', 'haneyyuṃ', 'bandheyyuṃ', 'pabbājeyyuṃ', 'vissaṭṭhi', 'sañcaritta', 'aññabhāgiya', 'evarūpaṃ',
         'vikappaṃ', 'aññatra', 'cīvarasmiṃ', 'nissaggiyaṃ', 'pācittiyaṃ', 'dhāretabbaṃ', 'kathina', 'tiṭṭhantu', 'jarā', 'mama']
CASES = {  # kind -> regex on the normalized text (ṁ is ṃ there)
    'aṃ end': r'aṃ\b', 'āṃ end': r'āṃ\b', 'iṃ end': r'iṃ\b', 'uṃ end': r'uṃ\b', 'tuṃ end': r'tt?uṃ\b',
    'ṃ before vowel': r'ṃ [aāiīuūeo]', 'ṃ mid': r'ṃ[a-zāīūṭḍṅñṇḷ]', 'ṭṭh': r'ṭṭh', 'ṇh': r'ṇh', 'ññ': r'ññ',
    'h start': r'\bh[aāiīuūeo]',
}


def score(text, have, named_have):
    t = normalize(text)
    s = sum(1 / (1 + have[k]) for k, rx in CASES.items() for _ in re.finditer(rx, t))
    return s + sum(3 for w in NAMED if w in t and not named_have[w])


if __name__ == '__main__':
    lines = {}
    for f in SOURCES:
        for k, v in json.load(open(f, encoding='utf-8')).items():
            v = v.strip()
            if 25 <= len(v) <= 110 and not v.endswith(':') and v not in lines.values():
                lines[k] = v
    have, named_have, picked = Counter(), Counter(), []
    pool = dict(lines)
    while len(picked) < N and pool:
        k = max(pool, key=lambda k: score(pool[k], have, named_have))
        t = normalize(pool.pop(k))
        picked.append({'id': k, 'text': lines[k]})
        for c, rx in CASES.items():
            have[c] += len(re.findall(rx, t))
        for w in NAMED:
            named_have[w] += w in t
    old = json.load(open('site/record/script.json', encoding='utf-8'))
    ids = {p['id'] for p in picked}
    json.dump(picked + [o for o in old if o['id'] not in ids], open('site/record/script.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    print(len(picked), 'focus lines, cases:', dict(have), '| named words missing:', [w for w in NAMED if not named_have[w]])
    print(sum(len(p['text']) for p in picked) // 14, 's of reading (about)')
