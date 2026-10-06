"""Kaggle dataset for a Russian Piper voice from the clone's clips (kaggle-clone-gen). Drops clips with stray sounds:
the owner heard mic-like noises in 3 of 30 (round clonegen2), always as an over-long pause or extra length -
so out go clips with an internal pause over 0.8 s and the slowest 8% by seconds per letter. Phonemes are what the
voice will get at run time: espeak via ruslan + our soft-sign fix (respell.ru_phonemes), stress marks removed;
ids from ruslan's map (the fine-tune starts from ruslan).
Usage (on f3): .venv/bin/python make_ru_voice_dataset.py /root/clone/gen2-out /root/clone/ru-voice-data
"""
import json
import os
import sys
import zipfile

import numpy as np
from piper import PiperVoice

from respell import ru_phonemes

SRC, OUT = sys.argv[1:3]
STRESS = '́'


def longest_pause(path):
    import wave
    w = wave.open(path)
    y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = 256
    rms = np.sqrt(np.convolve(y ** 2, np.ones(1024) / 1024, 'same')[::hop]) + 1e-9
    db = 20 * np.log10(rms)
    quiet = db < db.max() - 30
    best = run = 0
    for q in quiet[np.argmax(~quiet):len(quiet) - np.argmax(~quiet[::-1])]:  # inside the speech only
        run = run + 1 if q else 0
        best = max(best, run)
    return best * hop / w.getframerate()


voice = PiperVoice.load('models/ru_RU-ruslan-medium.onnx')
kept = json.load(open(f'{SRC}/kept.json', encoding='utf-8'))
os.makedirs(f'{OUT}/wavs', exist_ok=True)
with zipfile.ZipFile(f'{SRC}/clips.zip') as z:
    z.extractall(f'{OUT}/wavs')
for k in kept:
    k['plain'] = k['text'].replace(STRESS, '')
    k['spl'] = k['sec'] / max(len(k['plain']), 1)
    try:
        k['pause'] = longest_pause(f"{OUT}/wavs/{k['name']}.wav")
    except Exception:  # the job was killed mid-write: a broken last file
        k['pause'] = 99
slow = np.percentile([k['spl'] for k in kept], 92)
rows, dropped = [], 0
for k in kept:
    if k['pause'] > 0.8 or k['spl'] > slow:
        os.remove(f"{OUT}/wavs/{k['name']}.wav")
        dropped += 1
        continue
    sents = ru_phonemes(voice, k['plain'])
    ids = []
    for ph in sents:  # one clip may hold two short sentences: their ids one after another
        ids += voice.phonemes_to_ids(ph)
    rows.append(f"{k['name']}.wav|{k['plain']}|{' '.join(map(str, ids))}")
open(f'{OUT}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump(voice.config.phoneme_id_map, open(f'{OUT}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
for f in ('respell.py',):
    os.system(f'cp {f} {OUT}/')
json.dump({'title': 'ru-dg-voice-data', 'id': 'dhammagift/ru-dg-voice-data', 'licenses': [{'name': 'CC-BY-NC-SA-4.0'}]},
          open(f'{OUT}/dataset-metadata.json', 'w'))
print(len(rows), 'clips kept,', dropped, 'dropped,', f"{sum(k['sec'] for k in kept if k['pause'] <= 0.8 and k['spl'] <= slow) / 3600:.2f} h")
