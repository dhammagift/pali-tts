"""Round 55 (owner 2026-10-20: the ordinal on its own at a sutta's end - Paṭhamaṁ, Dutiyaṁ ... Dasamaṁ - comes out as
words that are not Pali at all, in the sutta mp3s). Now a lone word is read inside "W, W." with the first cut away
(tts_server.lone_word, round 50: the best of four, still often bad). Tried against it:
- after a real sutta end (abhinandunti, W.), the lead cut away the same way: a word after a phrase, not after itself;
- both with less randomness (noise 0.3 / 0.5 instead of 0.6 / 0.7): steadier, maybe flatter.
0.7x, one take each, blind. Usage (on f3): .venv/bin/python round55.py -> out/r55/; then build_page.py with ROUND = 'r55'
"""
import json
import os
import subprocess

import numpy as np

from pali_ipa import to_ipa, tune
from round31 import SR
from round50 import HOP, IDS, LENGTH, SESSION

OUT = 'out/r55'
WORDS = ['Paṭhamaṁ', 'Dutiyaṁ', 'Tatiyaṁ', 'Catutthaṁ', 'Pañcamaṁ', 'Chaṭṭhaṁ', 'Sattamaṁ', 'Aṭṭhamaṁ', 'Navamaṁ', 'Dasamaṁ']
LEAD = tune(to_ipa('abhinandunti,', full_a=True)) + ' '
VARIANTS = [('a', 'как сейчас (внутри «W, W.»)', 'self', (0.6, 0.7)),
            ('b', 'после конца сутты («abhinandunti, W.»)', 'lead', (0.6, 0.7)),
            ('c', 'как сейчас, ровнее', 'self', (0.3, 0.5)),
            ('d', 'после конца сутты, ровнее', 'lead', (0.3, 0.5))]


def cut(lead, ipa, noise):
    """Read lead + 'W.' and keep W only: the model's durations say where it starts."""
    ids = IDS['^'] + IDS['_']
    for c in lead + ipa + '.':
        ids += IDS[c] + IDS['_']
    ids += IDS['$']
    audio, dur = SESSION.run(None, {'input': np.array([ids], dtype=np.int64), 'input_lengths': np.array([len(ids)], dtype=np.int64),
                                    'scales': np.array([noise[0], LENGTH, noise[1]], dtype=np.float32)})
    audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
    starts = np.concatenate([[0], np.cumsum(dur)])
    a = starts[2 + 2 * len(lead)] - int(0.03 * SR)
    return np.concatenate([np.zeros(int(0.15 * SR), np.float32), audio[max(a, 0):]])


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, word in enumerate(WORDS):
        ipa = tune(to_ipa(word, full_a=True))
        vs = []
        for vid, label, how, noise in VARIANTS:
            f = f'o{i}.{vid}.mp3'
            audio = cut(f'{ipa}, ' if how == 'self' else LEAD, ipa, noise)
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': ipa})
        phrases.append({'id': f'o{i}', 'text': f'{word}. ({i + 1})', 'ipa': ipa, 'script': '', 'variants': vs,
                        'note': '★ где числительное прочитано правильно; ✗ где непонятное слово'})
    json.dump({'round': 'r55', 'sections': [{'id': 'o', 'title': 'Порядковые в конце сутты, 0.7x', 'multi_best': True,
                                             'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases) * len(VARIANTS))
