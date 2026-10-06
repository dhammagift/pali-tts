"""Round 32: arahaṁ read as «арахем» (round 31). Our phonemes ˈʌɾʌhən: the anusvara ending ən (round 29) after h
comes out as "em", and the stress is on the first syllable. Variants in the Iti pi so line, 2 takes, blind.
Usage (on f3): .venv/bin/python round32.py -> out/r32/; then build_page.py with ROUND = 'r32'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice

from pali_ipa import to_ipa, tune
from round31 import CFG, SR

OUT = 'out/r32'
TEXT = 'Itipi so bhagavā arahaṁ sammāsambuddho vijjācaraṇasampanno sugato lokavidū.'
V = [('a', 'как сейчас: ˈʌɾʌhən', lambda s: s),
     ('b', 'полное «а» в окончании: ˈʌɾʌhʌn', lambda s: s.replace('ˈʌɾʌhən', 'ˈʌɾʌhʌn')),
     ('c', 'ударение на «ра»: ʌɾˈʌhʌn', lambda s: s.replace('ˈʌɾʌhən', 'ʌɾˈʌhʌn')),
     ('d', 'ударение на «хаṁ»: ʌɾʌhˈʌn', lambda s: s.replace('ˈʌɾʌhən', 'ʌɾʌhˈʌn'))]

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    base = tune(to_ipa(TEXT, full_a=True))
    vs = []
    for vid, label, fn in V:
        s = fn(base)
        assert vid == 'a' or s != base, vid
        for take in (1, 2):
            audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
            f = f'p0.{vid}{take}.mp3'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
    json.dump({'round': 'r32', 'sections': [{'id': 'p', 'title': 'arahaṁ', 'multi_best': False, 'phrases': [
        {'id': 'p0', 'text': TEXT, 'ipa': base, 'script': '', 'variants': vs, 'note': '★ где arahaṁ звучит правильно'}]}]},
        open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
