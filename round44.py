"""Round 44: a female Pali voice. Piper hi_IN-priyamvada (♀, same CC BY-NC-SA licence and the same phoneme map as
pratham) fed our IPA with the rules tuned for pratham (r32), against pratham itself. 12 of round 37's hard and
common stock phrases, 0.7x, 2 takes each, blind. Shows how much of the pratham tuning carries over.
Usage (on f3): .venv/bin/python round44.py -> out/r44/; then build_page.py with ROUND = 'r44'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR
from round37 import PHRASES, clean

OUT = 'out/r44'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
PICK = [0, 1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 13]  # round 37's phrases minus the longest repeats
VOICES = [('a', 'pratham ♂', 'hi_IN-pratham-medium'), ('b', 'priyamvada ♀', 'hi_IN-priyamvada-medium')]

if __name__ == '__main__':
    voices = {vid: PiperVoice.load(f'models/{m}.onnx') for vid, _, m in VOICES}
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i in PICK:
        ref, text = PHRASES[i]
        s = tune(to_ipa(clean(text), full_a=True))
        vs = []
        for vid, label, _ in VOICES:
            for take in (1, 2):
                audio = voices[vid].phoneme_ids_to_audio(voices[vid].phonemes_to_ids(list(s)), CFG)
                f = f'v{i}.{vid}{take}.mp3'
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', str(SR), '-q:a', '7', f'{OUT}/{f}'],
                               input=audio.astype(np.float32).tobytes(), check=True)
                vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
        phrases.append({'id': f'v{i}', 'text': f'{text} ({ref})', 'ipa': s, 'script': '', 'variants': vs,
                        'note': '★ где лучше; ✗ где плохо'})
    json.dump({'round': 'r44', 'sections': [{'id': 'v', 'title': 'pratham ♂ / priyamvada ♀, одни и те же правила, 0.7x',
                                             'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for p in phrases))
