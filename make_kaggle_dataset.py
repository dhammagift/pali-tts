"""Pack the aligned clips into a Kaggle dataset for Piper fine-tuning.

Keeps clips with alignment score >= 0.6 and no word below 0.2; drops files whose text the reading does not match.
Phoneme ids use the rohan checkpoint's map (we warm-start from it), plain IPA without pratham's tweaks:
the fine-tuned voice learns the owner's real pronunciation, it only needs consistent symbols.
Usage: .venv/bin/python make_kaggle_dataset.py data/full/rev/clips.json data/full/train/train/wavs data/kaggle
"""
import json
import os
import shutil
import sys

from piper import PiperVoice

from pali_ipa import to_ipa

DROP_FILES = {'Bu-pbkc1var'}  # 0.7 of 3.8 min aligned: reads a text variant not in SC
clips_path, wav_dir, out = sys.argv[1:4]
voice = PiperVoice.load('models/hi_IN-rohan-medium.onnx')
os.makedirs(f'{out}/wavs', exist_ok=True)
rows = []
for c in json.load(open(clips_path, encoding='utf-8')):
    if c['item'] in DROP_FILES or c['score'] < 0.6 or c['min_score'] < 0.2:
        continue
    ipa = to_ipa(c['text'], full_a=True)
    ids = voice.phonemes_to_ids(list(ipa))
    shutil.copy(f"{wav_dir}/{c['name']}.wav", f"{out}/wavs/{c['name']}.wav")
    rows.append(f"{c['name']}.wav|{c['text']}|{' '.join(map(str, ids))}")
open(f'{out}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
json.dump(voice.config.phoneme_id_map, open(f'{out}/phonemes.json', 'w', encoding='utf-8'), ensure_ascii=False)
shutil.copy('pali_ipa.py', out)
json.dump({'title': 'pali-voice-v1', 'id': 'dhammagift/pali-voice-v1', 'licenses': [{'name': 'CC-BY-NC-SA-4.0'}]},
          open(f'{out}/dataset-metadata.json', 'w'))
print(len(rows), 'clips')
