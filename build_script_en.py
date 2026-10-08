"""Recording script for an English voice (a friend of the owner): sentences from Bhikkhu Sujato's English
translations on SuttaCentral, so Pali names and terms (Sāvatthī, bhikkhu, Tathāgata) are in the data too.
Picked like build_script.py: greedy cover of phoneme pairs (espeak en-us, as Piper's English voices are trained),
best lines first, so a session stopped halfway still covers the most.
Usage: .venv/bin/python build_script_en.py -> site/record-en/script.json
"""
import glob
import heapq
import json
import os
import re
from collections import Counter

from piper import PiperVoice

ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/translation/en/sujato/sutta'
TARGET_MIN = 150  # the ideal case; the first lines matter most
WANT = 4
SENT = re.compile(r'(?<=[.!?;])\s+')
GOOD = re.compile(r"^[A-Za-zĀāĪīŪūṬṭḌḍṄṅÑñṆṇḶḷṀṁṂṃ ,.!?;:’'\-—]+$")
voice = PiperVoice.load('models/en_GB-alan-medium.onnx')


def units(text):
    ph = ' '.join(''.join(s) for s in voice.phonemize(text))
    out = []
    for w in re.findall(r"[^\s,.!?;:—\-]+", ph.replace('ˈ', '').replace('ˌ', '')):
        t = ['#'] + list(w) + ['#']
        out += [a + '_' + b for a, b in zip(t, t[1:])]
    return out


def seconds(text):  # calm reading: ~2.6 words a second plus a breath
    return 0.8 + len(text.split()) / 2.6


cands, seen = [], set()
for f in sorted(glob.glob(f'{ROOT}/**/*.json', recursive=True)):
    for sid, text in json.load(open(f, encoding='utf-8')).items():
        if ':0.' in sid:
            continue
        for k, s in enumerate(SENT.split(text.strip().replace('“', '').replace('”', '').replace('‘', ''))):
            s = s.strip(' ’')
            key = re.sub(r'[^a-z]', '', s.lower())
            if not 30 <= len(s) <= 170 or not GOOD.match(s) or key in seen or s.count('—') > 1:
                continue
            seen.add(key)
            cands.append((f'{sid}.{k}' if k else sid, s))
# a reader should not stumble: at most one rare word (a name, mostly Pali) in a line
freq = Counter(w for _, s in cands for w in re.findall(r"[a-zāīūṭḍṅñṇḷṁṃ’']+", s.lower()))
cands = [(sid, s) for sid, s in cands if sum(freq[w] < 20 for w in re.findall(r"[a-zāīūṭḍṅñṇḷṁṃ’']+", s.lower())) <= 1]
print(len(cands), 'candidates')
cands = [(sid, s, Counter(units(s)), seconds(s)) for sid, s in cands]
have = Counter()


def gain(c):
    return sum(min(n, max(0, WANT - have[u])) / (1 + have[u]) for u, n in c[2].items()) / c[3]


heap = [(-gain(c), i) for i, c in enumerate(cands)]
heapq.heapify(heap)
picked, total = [], 0.0
while heap and total < TARGET_MIN * 60:
    g, i = heapq.heappop(heap)
    fresh = gain(cands[i])
    if heap and fresh < -heap[0][0] - 1e-9:
        heapq.heappush(heap, (-fresh, i))
        continue
    sid, text, us, sec = cands[i]
    picked.append({'id': sid, 'text': text})
    have.update(us)
    total += sec

# the first 100 are the friend's test session: plain English first, names later (the set stays the same)
rare = lambda t: sum(freq[w] < 20 for w in re.findall(r"[a-zāīūṭḍṅñṇḷṁṃ’']+", t.lower()))
picked[:100] = sorted(picked[:100], key=lambda p: rare(p['text']))
os.makedirs('site/record-en', exist_ok=True)
json.dump(picked, open('site/record-en/script.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
mins = [round(sum(c[3] for c in cands if c[0] in {p['id'] for p in picked[:n]}) / 60) for n in (100, 300, 1000)]
print(f'{len(picked)} lines, ~{total / 60:.0f} min; first 100/300/1000 lines ~{mins} min; {len(have)} phoneme pairs')
assert units('Evam') and all('_' in u for u in units('the Buddha'))
