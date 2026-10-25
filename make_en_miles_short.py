"""Short lines for Miles's voice (owner 2026-10-25): Yojanāni trained on miles2 (2250 ElevenLabs sentences in his cloned
voice, shortest 2 words, median 9) reads a word on its own badly ("monks" alone as "next"): it never heard one. Here the
same ElevenLabs voice reads Sujato's real short segments (1-3 words: "What five?", "Chapter One", "Mendicants!") and the
most frequent words one by one, to add to the dataset. No Pali and no diacritics: ElevenLabs would read them its own
way, not by our rules. Resumable: an existing mp3 is not paid for again.
Usage (on f3): python3 make_en_miles_short.py /root/miles2-short [max chars] [--dry]
"""
import collections
import glob
import json
import os
import random
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from respell import EN_PALI_WORDS  # noqa: E402

OUT = sys.argv[1]
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 33000
DRY = '--dry' in sys.argv
TR = os.environ.get('SC_TR', '/root/sc-translation')
env = dict(line.split('=', 1) for line in open('/root/.secrets/tools.env').read().splitlines() if '=' in line and not line.startswith('#'))
KEY, VOICE = (env[k].strip().strip('"\'') for k in ('EL_TOKEN', 'EL_VOICE_MILES'))
SETTINGS = {'stability': 0.5, 'similarity_boost': 0.75, 'style': 0.0, 'use_speaker_boost': True, 'speed': 1.0}  # as miles2

plain = lambda t: re.fullmatch(r"[A-Za-z][A-Za-z ,.?!:;’'-]*", t) and not any(w.lower().strip("’'") in EN_PALI_WORDS
                                                                              for w in re.findall(r"[A-Za-z’']+", t))
short, words, caps = collections.Counter(), collections.Counter(), collections.Counter()
for f in glob.glob(f'{TR}/en/sujato/sutta/**/*.json', recursive=True):
    for t in json.load(open(f, encoding='utf-8')).values():
        for w in re.findall(r"[\w’']+", t):  # \w: "Licchavīs" whole, so the diacritic keeps it out
            words[w.lower()] += 1
            caps[w.lower()] += w[0].isupper()
        t = re.sub(r'[“”‘]|’(?=\s|$)|\s*…\s*', ' ', t).strip()  # quotes and ellipses off: the words alone
        if t and len(t.split()) <= 3 and plain(t):
            short[t] += 1
rnd, lines, seen = random.Random(2026), [], set()
for t, _ in short.most_common():  # real short lines first, the most frequent first
    if t.lower().strip(' .,?!:;') not in seen:
        seen.add(t.lower().strip(' .,?!:;'))
        lines.append(t)
    if sum(map(len, lines)) > BUDGET * 0.6:
        break
for w, _ in words.most_common():  # then single words, half as a heading ("Feeling."), half bare ("feeling")
    if w not in seen and len(w) > 1 and plain(w) and caps[w] < words[w] / 2:  # mostly capitalized: a name
        seen.add(w)
        lines.append(w.capitalize() + '.' if len(w) > 3 and rnd.random() < 0.5 else w)  # no "The." as a heading
    if sum(map(len, lines)) > BUDGET:
        break
print(len(lines), 'lines,', sum(map(len, lines)), 'chars; first:', lines[:8], 'last:', lines[-4:])
if DRY:
    sys.exit()
os.makedirs(f'{OUT}/mp3', exist_ok=True)


def tts(i):
    path = f'{OUT}/mp3/s{i:05d}.mp3'
    if not os.path.exists(path):
        r = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128',
                                   json.dumps({'text': lines[i], 'model_id': 'eleven_multilingual_v2', 'voice_settings': SETTINGS}).encode(),
                                   {'xi-api-key': KEY, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                data = resp.read()
        except Exception as e:
            print('failed', i, lines[i], e, flush=True)
            return
        open(path + '.tmp', 'wb').write(data)
        os.replace(path + '.tmp', path)
    return i


done = [i for i in ThreadPoolExecutor(3).map(tts, range(len(lines))) if i is not None]
open(f'{OUT}/metadata.csv', 'w', encoding='utf-8').write(''.join(f's{i:05d}.mp3|{lines[i]}\n' for i in done))
print(len(done), 'of', len(lines), 'clips in', OUT)
