"""Round 48: Tiṭṭhatu read «чичату». Rounds 46-47: every spelling of ṭṭh (ʈːʰ, ʈː + h, ʈː + ɦ, no aspiration, tense i)
failed in Tiṭṭhatu (stress on ti), while Tiṭṭhantu as it is (stress on the second syllable) was ok 3 of 4. So the
stress: on the second syllable, or none; with tiṭṭhati too (416 times in the canon, the same stress on ti).
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round48.py -> out/r48/; then build_page.py with ROUND = 'r48'
"""
import json
import re
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r48'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('titth', 'tiṭṭhatu, tiṭṭhati: «чичату»', '★ где «титтхату» / «титтхати», без «ч»',
     ['Tiṭṭhatu, bhikkhave, ekaṁ vassaṁ.', 'Ucchinnabhavanettiko, bhikkhave, tathāgatassa kāyo tiṭṭhati.'],
     [('a', 'как сейчас (ударение на ti)', lambda s: s),
      ('b', 'ударение на второй слог (как Tiṭṭhantu)', lambda s: re.sub(r'tˈɪʈːʰ([ʌa])', r'tɪʈːʰˈ\1', s)),
      ('c', 'без ударения', lambda s: s.replace('tˈɪʈːʰ', 'tɪʈːʰ'))]),
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
                    f = f'{sid}{i}.{vid}{take}.mp3'
                    vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
                    if os.path.exists(f'{OUT}/{f}'):  # rendered before: keep the take that was voted on
                        continue
                    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                    '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title + ', 0.7x', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'r48', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
