"""Piper students of Supertonic M1 (kaggle-ru-stm1, one per base voice) against their teacher M1 and today's ruslan:
the 5 Russian lines of st1. Every finished run in /root/st-m1/runs/<base>/ is taken; rerun as more finish.
Blind; Piper students read like tts_server reads Russian (espeak via the voice + respell.ru_phonemes).
Usage (on f3): .venv/bin/python round_stm1.py -> out/stm1/; then build_page.py with ROUND = 'stm1'
"""
import glob
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice

from respell import ru_phonemes
from round_st1 import TEXTS, mp3

OUT = 'out/stm1'
RUNS = '/root/st-m1/runs'


def piper_audio(voice, text):
    parts = []
    for ph in ru_phonemes(voice, text):
        parts += [voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph)), np.zeros(int(voice.config.sample_rate * 0.35), np.float32)]
    return np.concatenate(parts), voice.config.sample_rate


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    voices = [('ruslan', 'ruslan сейчас', PiperVoice.load('models/ru_RU-ruslan-medium.onnx'))]
    for d in sorted(glob.glob(f'{RUNS}/*/ru_stm1-medium.onnx')):
        base = d.split('/')[-2]
        if not base.endswith('-smoke'):
            voices.append((f'st-{base}', f'ученик M1 от {base} (Piper)', PiperVoice.load(d, config_path=d + '.json')))
    phrases = []
    for i, text in enumerate(TEXTS['ru']):
        vs = [{'id': 'm1', 'label': 'Supertonic M1 (учитель)', 'file': f'ru{i}.m1.mp3', 'sent': text}]
        subprocess.run(['cp', f'out/st1/ru{i}.a.mp3', f'{OUT}/ru{i}.m1.mp3'], check=True)  # the M1 take rated in st1
        for vid, label, voice in voices:
            audio, sr = piper_audio(voice, text)
            mp3(audio, sr, f'{OUT}/ru{i}.{vid}.mp3')
            vs.append({'id': vid, 'label': label, 'file': f'ru{i}.{vid}.mp3', 'sent': text})
        phrases.append({'id': f'ru{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучший; ok — годится; ✗ — плохо (шум, металл, ошибки, монотонно)'})
    json.dump({'round': 'stm1', 'sections': [{'id': 'ru', 'title': 'Русский: ученики M1 на Piper', 'multi_best': False,
                                              'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', [v[0] for v in voices])
