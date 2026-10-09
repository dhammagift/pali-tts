"""Round 49: ṭṭh still read «ч» (owner, Pātimokkha in the app: Tiṭṭhantu «тичанту», Uddiṭṭhaṁ, Niṭṭhite, Sukkavissaṭṭhi).
Tried since round 20: ʈʈʰ, ʈʰ, ʈːʰ (now), ʈʈ, dental ttʰ, ʈː+h, ʈː+ɦ, ʈː - none stable; stress (round 48) is not it
either: Tiṭṭhantu already has it on the second syllable. The «ч» is the release of the aspirated retroflex, so new here:
the closure retroflex, the release dental and aspirated (ʈtʰ); and the dental ttʰ again in these words.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round49.py -> out/r49/; then build_page.py with ROUND = 'r49'
"""
import json
import re
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r49'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('tth', 'ṭṭh: «ч» вместо «ттх»', '★ где «ттх», без «ч»',
     ['Tiṭṭhantu, bhikkhave, satta vassāni.', 'Uddiṭṭhaṁ kho āyasmanto nidānaṁ.', 'Niṭṭhite navakamme ca, Sukkavissaṭṭhi.'],
     [('a', 'как сейчас (ʈːʰ)', lambda s: s),
      ('b', 'смычка ретрофлексная, взрыв зубной с придыханием (ʈtʰ)', lambda s: s.replace('ʈːʰ', 'ʈtʰ')),
      ('c', 'зубное ttʰ', lambda s: s.replace('ʈːʰ', 'ttʰ')),
      ('d', 'ʈː + отдельное h', lambda s: s.replace('ʈːʰ', 'ʈːh'))]),
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
    json.dump({'round': 'r49', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
