"""Clips for a Piper voice with Supertonic 3's M1 timbre and manner (owner, st1: M1 best in 9 of 10 lines; Piper keeps
the speed: Supertonic is ~1.6x realtime on f3, Piper ~8x). Sentences from DG's Russian translations
(make_ru_corpus.py), read by M1 as rated in st1 (8 steps, speed 1.05), 22050 Hz mono 16-bit like the dgru data.
Resumable: clips already in OUT/wavs are kept. Writes OUT/kept.json and OUT/clips.zip for make_ru_voice_dataset.py.
Usage (f3, low priority: the live voice service shares the CPU):
  python3 make_ru_corpus.py /var/www/dg-node-prod/dg.db 2600 > /root/st-m1/sentences.txt
  nice -n 19 .venv-ears/bin/python gen_supertonic_ru.py /root/st-m1 [hours]
"""
import json
import os
import subprocess
import sys
import zipfile

import numpy as np

from round_st1 import ST
from helper import load_text_to_speech, load_voice_style

OUT = sys.argv[1]
HOURS = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
SR = 22050

if __name__ == '__main__':
    tts = load_text_to_speech(f'{ST}/assets/onnx')
    style = load_voice_style([f'{ST}/assets/voice_styles/M1.json'])
    os.makedirs(f'{OUT}/wavs', exist_ok=True)
    texts = [t.strip() for t in open(f'{OUT}/sentences.txt', encoding='utf-8') if t.strip()]
    kept_path = f'{OUT}/kept.json'
    kept = json.load(open(kept_path, encoding='utf-8')) if os.path.exists(kept_path) else []
    done = {k['name'] for k in kept}
    total = sum(k['sec'] for k in kept)
    for i, text in enumerate(texts):
        if total >= HOURS * 3600:
            break
        name = f's{i:05d}'
        if name in done:
            continue
        wav, dur = tts(text, 'ru', style, 8, 1.05)
        audio = wav.reshape(-1)[:int(tts.sample_rate * float(dur[0]))].astype(np.float32)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(tts.sample_rate), '-ac', '1', '-i', '-',
                        '-ar', str(SR), '-c:a', 'pcm_s16le', f'{OUT}/wavs/{name}.wav'], input=audio.tobytes(), check=True)
        kept.append({'name': name, 'text': text, 'sec': round(len(audio) / tts.sample_rate, 2)})
        total += kept[-1]['sec']
        if len(kept) % 25 == 0:  # progress survives a kill
            json.dump(kept, open(kept_path + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False)
            os.replace(kept_path + '.tmp', kept_path)
            print(f'{len(kept)} clips, {total / 3600:.2f} h', flush=True)
    json.dump(kept, open(kept_path, 'w', encoding='utf-8'), ensure_ascii=False)
    with zipfile.ZipFile(f'{OUT}/clips.zip', 'w') as z:
        for k in kept:
            z.write(f"{OUT}/wavs/{k['name']}.wav", f"{k['name']}.wav")
    print('done', len(kept), 'clips', f'{total / 3600:.2f} h')
