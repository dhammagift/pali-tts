"""Round 45: So before a vowel. Owner after round 43: no pause after So at all, but its o must stay long. Now (r33):
before i So is joined with a triple oː (~230 ms, rounds 38-40); before e round 17's pause stays (joined gave «сори»).
Checks the long joined So before i, and the same before e. 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round45.py -> out/r45/; then build_page.py with ROUND = 'r45'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r45'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('i', 'So перед i: без паузы, o долгое', '★ где So вместе с фразой и o долгое',
     ['So imameva kāyaṁ upasaṁharati.', 'So idha, bhikkhave, bhikkhu.'],
     [('a', 'как сейчас: тройное oː без паузы', lambda s: s),
      ('b', 'одно oː без паузы (раунд 43, вариант d)', lambda s: s.replace('soːoːoː ', 'soː ', 1))]),
    ('e', 'So перед e', '★ где So вместе с фразой, o долгое и без «сори»',
     ['So evamāha.', 'So evaṁ pajānāti.'],
     [('a', 'как сейчас: пауза (раунд 17)', lambda s: s),
      ('b', 'тройное oː без паузы', lambda s: s.replace('sˈoː, ', 'soːoːoː ', 1))]),
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
    json.dump({'round': 'r45', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
