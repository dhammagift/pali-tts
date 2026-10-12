"""Which Piper student of Supertonic M1 to train on (owner 2026-10-12: «добей»): step 1 of 2, on f3 in .venv.
40 Russian lines of SuttaCentral translations (none of the training texts) read by every student as tts_server reads
Russian -> /root/st-m1/eval/<base>/NN.wav + texts.json. Step 2: eval/stm1_score.py in /root/venv-ml.
"""
import glob
import json
import os
import random
import re
import wave

import numpy as np
from piper import PiperVoice

from round_stm1 import piper_audio, RUNS

OUT = '/root/st-m1/eval'
train = {l.split('|')[1].strip() for l in open('/root/st-m1/data/metadata.csv', encoding='utf-8')}
lines = []
for f in sorted(glob.glob('/root/sc-translation/ru/sv/**/*.json', recursive=True)):
    for t in json.load(open(f, encoding='utf-8')).values():
        t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', t)).strip()
        if 60 <= len(t) <= 180 and re.fullmatch(r'[А-Яа-яЁё ,.;:!?—«»“”"\'()-]+', t) and t not in train:
            lines.append(t)
random.seed(1)
texts = random.sample(sorted(set(lines)), 40)
os.makedirs(OUT, exist_ok=True)
json.dump(texts, open(f'{OUT}/texts.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for d in sorted(glob.glob(f'{RUNS}/*/ru_stm1-medium.onnx')):
    base = d.split('/')[-2]
    if base.endswith('-smoke'):
        continue
    voice = PiperVoice.load(d, config_path=d + '.json')
    os.makedirs(f'{OUT}/{base}', exist_ok=True)
    for i, t in enumerate(texts):
        audio, sr = piper_audio(voice, t)
        with wave.open(f'{OUT}/{base}/{i:02d}.wav', 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    print(base, 'ok', flush=True)
