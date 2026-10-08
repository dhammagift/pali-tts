"""Round 40: the word-final o only. Rounds 38-39: every spelling sounded short («длина же должна быть одинаковой у
длинного аа и оо»). Measured with the duration model (align onnx, 0.7x): a final oː lasts 100-140 ms, the stressed aː
of sampajāno 139 ms; round 39's ˈoː / ɔːː / oːˑ were only 120-160 ms. These are 170-240 ms. 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round40.py -> out/r40/; then build_page.py with ROUND = 'r40'
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r40'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
END_O = re.compile(r'(?<=[^ ,])oː(?=[ ,.?!:;]|$)')  # a word-final long o


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('o', 'Конечное -o, длиннее (замерено: сейчас ~110 мс, ударное ā ~140 мс)', '★ где конечное о как долгое ā',
     ['Ātāpī sampajāno satimā.', 'Sammāsambuddho vijjācaraṇasampanno sugato lokavidū.'],
     [('a', 'как сейчас, ~110 мс', lambda s: s),
      ('b', 'ударное + полудолгота, ~170 мс', lambda s: END_O.sub('ˈoːˑ', s)),
      ('c', 'ударное двойное, ~200 мс', lambda s: END_O.sub('ˈoːoː', s)),
      ('d', 'открытое ударное ɔːː, ~200 мс', lambda s: END_O.sub('ˈɔːː', s)),
      ('e', 'тройное, ~230 мс', lambda s: END_O.sub('oːoːoː', s))]),
]

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, note, texts, variants in SECTIONS:
        phrases = []
        for i, text in enumerate(texts):
            base = tune(to_ipa(text, full_a=True))
            vs = []
            for vid, label, fn in variants:
                s = fn(base)
                assert vid == 'a' or s != base, (sid, vid, base)
                for take in (1, 2):
                    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
                    f = f'{sid}{i}.{vid}{take}.mp3'
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                    '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
                    vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title + ', 0.7x', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'r40', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
