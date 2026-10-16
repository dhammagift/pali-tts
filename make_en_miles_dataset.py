"""Kaggle dataset for a Piper voice from Miles's readings of the record-en script (owner 2026-10-16: a demo on the first
100 lines; more may come). <n>.<n>.wav in SRC is script line n; 48 kHz -> 22050 mono 16-bit, edge silence trimmed.
Phonemes are what tts_server gives an English voice (respell.en_phonemes: espeak en-us + our phonemes for Pali words),
ids from ryan's map (the fine-tune starts from en_US-ryan-medium).
Usage (on f3): .venv/bin/python make_en_miles_dataset.py /var/www/en-tts/1-100 /root/en-miles/data [dataset name]
"""
import glob
import json
import os
import re
import subprocess
import sys

from piper import PiperVoice

from respell import en_phonemes

SRC, OUT = sys.argv[1:3]
NAME = sys.argv[3] if len(sys.argv) > 3 else 'en-miles-voice-data'
SCRIPT = json.load(open('site/record-en/script.json', encoding='utf-8'))
TRIM = 'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse'

voice = PiperVoice.load('models/en_US-ryan-medium.onnx')
os.makedirs(f'{OUT}/wavs', exist_ok=True)
rows = []
for f in sorted(glob.glob(f'{SRC}/*.wav'), key=lambda f: int(re.match(r'(\d+)', os.path.basename(f)).group(1))):
    n = int(re.match(r'(\d+)', os.path.basename(f)).group(1))
    text, name = SCRIPT[n - 1]['text'], f'm{n:04d}'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f, '-af', TRIM, '-ar', '22050', '-ac', '1', '-c:a', 'pcm_s16le',
                    f'{OUT}/wavs/{name}.wav'], check=True)
    rows.append(f"{name}.wav|{text}|{' '.join(map(str, voice.phonemes_to_ids(en_phonemes(voice, text))))}")
open(f'{OUT}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump(voice.config.phoneme_id_map, open(f'{OUT}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in ('respell.py', 'pali_ipa.py', 'stress_names.tsv'):  # respell imports pali_ipa and reads the names
    os.system(f'cp {f} {OUT}/')
json.dump({'title': NAME, 'id': f'dhammagift/{NAME}', 'licenses': [{'name': 'CC-BY-NC-SA-4.0'}]},
          open(f'{OUT}/dataset-metadata.json', 'w'))
print(len(rows), 'clips')
