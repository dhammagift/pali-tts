"""Kaggle dataset for a Piper voice from Miles's readings of the record-en script (owner 2026-10-16: a demo on the first
100 lines; more may come). <k>.<n>.wav anywhere under SRC is script line n (k counts within a batch: 101-200/96.196.wav is line 196); 48 kHz -> 22050 mono 16-bit, edge silence trimmed at -60 dB, 0.15 s kept at the end.
Phonemes are what tts_server gives an English voice (respell.en_phonemes: espeak en-us + our phonemes for Pali words),
ids from ryan's map (the fine-tune starts from en_US-ryan-medium).
Usage (on f3): .venv/bin/python make_en_miles_dataset.py /var/www/en-tts /root/en-miles/data [dataset name]
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
# -60 dB, not -45: the takes are clean (floor ~-75 dB) and -45 also cut each line's fading last sound, so the voice
# learnt to stop a split second early (Miles and owner, miles2, 2026-10-17); 0.15 s of silence after, as a voice ends
TRIM = ('silenceremove=start_periods=1:start_threshold=-60dB,areverse,silenceremove=start_periods=1:start_threshold=-60dB,'
        'areverse,apad=pad_dur=0.15')

voice = PiperVoice.load('models/en_US-ryan-medium.onnx')
os.makedirs(f'{OUT}/wavs', exist_ok=True)
rows = []
line = lambda f: int(re.match(r'\d+\.(\d+)\.wav$', os.path.basename(f)).group(1))
takes = sorted(glob.glob(f'{SRC}/**/*.wav', recursive=True), key=line)
# a lost take must stop the build, not shrink the dataset (owner 2026-10-17: gdown dropped 11 of 101-200 unnoticed)
got = [line(f) for f in takes]
want = set(range(1, max(got) + 1))  # and the whole range of every <a>-<b> batch folder, so a lost last take shows too
for d in glob.glob(f'{SRC}/**/', recursive=True):
    if r := re.fullmatch(r'(\d+)-(\d+)', os.path.basename(os.path.normpath(d))):
        want |= set(range(int(r[1]), int(r[2]) + 1))
missing = sorted(want - set(got))
dups = sorted({n for n in got if got.count(n) > 1})
if missing or dups:
    sys.exit(f'missing script lines {missing}, duplicated {dups}: fetch them (fetch_drive.py) before training')
for f in takes:
    n = line(f)
    text, name = SCRIPT[n - 1]['text'], f'm{n:04d}'
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', f, '-af', TRIM, '-ar', '22050', '-ac', '1', '-c:a', 'pcm_s16le',
                    f'{OUT}/wavs/{name}.wav'], check=True)
    rows.append(f"{name}.wav|{text}|{' '.join(map(str, voice.phonemes_to_ids(en_phonemes(voice, text))))}")
open(f'{OUT}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump(voice.config.phoneme_id_map, open(f'{OUT}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in ('respell.py', 'pali_ipa.py', 'stress_names.tsv', 'ru_yo.tsv'):  # respell imports pali_ipa and reads these
    os.system(f'cp {f} {OUT}/')
json.dump({'title': NAME, 'id': f'dhammagift/{NAME}', 'licenses': [{'name': 'CC-BY-NC-SA-4.0'}]},
          open(f'{OUT}/dataset-metadata.json', 'w'))
print(len(rows), 'clips')
