"""Round 56 (owner 2026-10-23): «Idamavoca bhagavā.» read as «Юхагала», «…cittāni vimucciṁsūti.» as «вимучинсукьи»,
pharitvā as «фаритва». The phonemes are right in all three: the model misreads them.
- Idamavoca bhagavā. (a line of its own, 205 times in the suttas): two words alone go as wrong as one (round 50);
  read after a sutta's own last word and cut there, as a lone word is now (round 55), with its noise or steadier;
- vimucciṁsūti. (a long sentence's last word): the last syllable spoilt - read with more speech after it and cut
  there (as Miles's voice, round miles5), or steadier;
- pharitvā: pʰ as f; p + a separate h (rounds 33, 46-47) is now the rule for every ph: checked against pʰ.
0.7x, one take each, blind. Usage (on f3): .venv/bin/python round56.py -> out/r56/; then build_page.py with ROUND = 'r56'
"""
import json
import os
import subprocess

import numpy as np

from pali_ipa import to_ipa, tune
from round31 import SR
from round50 import HOP, IDS, LENGTH, SESSION

OUT = 'out/r56'
LEAD = tune(to_ipa('abhinandunti,', full_a=True)) + ' '
TAIL = ' ' + tune(to_ipa('abhinandunti', full_a=True))
NOW, STEADY = (0.6, 0.7), (0.3, 0.5)


def synth(ipa, lead='', tail='', noise=NOW):
    """Read lead + ipa + tail and keep ipa only, cut where the model's own durations say it starts and ends."""
    ids = IDS['^'] + IDS['_']
    for c in lead + ipa + tail:
        ids += IDS[c] + IDS['_']
    ids += IDS['$']
    audio, dur = SESSION.run(None, {'input': np.array([ids], dtype=np.int64), 'input_lengths': np.array([len(ids)], dtype=np.int64),
                                    'scales': np.array([noise[0], LENGTH, noise[1]], dtype=np.float32)})
    audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
    starts = np.concatenate([[0], np.cumsum(dur)])
    a = starts[2 + 2 * len(lead)] - int(0.03 * SR) if lead else 0
    b = starts[2 + 2 * (len(lead) + len(ipa))] if tail else len(audio)
    out = audio[max(a, 0):b].astype(np.float32)
    if tail:
        fade = int(0.03 * SR)
        out[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    return np.concatenate([np.zeros(int(0.15 * SR), np.float32), out, np.zeros(int(0.3 * SR), np.float32)])


def ipa(text):
    return tune(to_ipa(text, full_a=True))


IDAM = ipa('Idamavoca bhagavā.')
VIM = ipa('Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.')
PHAR = ipa('Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.')
PHRASES = [
    ('i', 'Idamavoca bhagavā.', [('a', 'как сейчас', lambda: synth(IDAM)),
                                 ('b', 'после конца сутты', lambda: synth(IDAM, lead=LEAD)),
                                 ('c', 'после конца сутты, ровнее', lambda: synth(IDAM, lead=LEAD, noise=STEADY))]),
    ('v', 'Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.',
     [('a', 'как сейчас', lambda: synth(VIM)),
      ('b', 'с продолжением, отрезанным', lambda: synth(VIM, tail=TAIL)),
      ('c', 'ровнее', lambda: synth(VIM, noise=STEADY))]),
    ('p', 'Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.',
     [('a', 'ph слитно (было)', lambda: synth(PHAR.replace('ph', 'pʰ'))),
      ('b', 'p + h (новое правило)', lambda: synth(PHAR))]),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for pid, text, variants in PHRASES:
        vs = []
        for vid, label, fn in variants:
            f = f'{pid}.{vid}.mp3'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-q:a', '7', f'{OUT}/{f}'], input=fn().tobytes(), check=True)
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': ''})
        phrases.append({'id': pid, 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучше всех; ✓ правильно; ✗ неправильно (что слышно)'})
    json.dump({'round': 'r56', 'sections': [{'id': 'p', 'title': 'Idamavoca bhagavā, vimucciṁsūti, pharitvā; 0.7x',
                                             'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for p in phrases))
