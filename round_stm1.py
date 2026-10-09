"""Piper students of Supertonic M1 (kaggle-ru-stm1, one per base voice) and the owner's own voice, blind, on the 5
Russian lines of st1; under each line, openly labelled and not part of the round (owner): old Piper voices + M1.
Every finished run in /root/st-m1/runs/<base>/ is taken; rerun as more finish.
Piper voices read like tts_server reads Russian (espeak via the voice + respell.ru_phonemes).
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
    # blind: the students and the owner's own voice; reference (open labels, not rated as a round): old Piper + M1
    blind = [('dgru', 'твой голос (dgru)', PiperVoice.load('models/ru_dg2-medium.onnx'))]
    for d in sorted(glob.glob(f'{RUNS}/*/ru_stm1-medium.onnx')):
        base = d.split('/')[-2]
        if not base.endswith('-smoke'):
            blind.append((f'st-{base}', f'ученик M1 от {base}', PiperVoice.load(d, config_path=d + '.json')))
    old = [(f'old-{v}', f'OLD {v} (Piper)', PiperVoice.load(f'models/ru_RU-{v}-medium.onnx')) for v in ('ruslan', 'irina', 'denis', 'dmitri')]
    sections = []
    for i, text in enumerate(TEXTS['ru']):
        def render(vid, voice):
            audio, sr = piper_audio(voice, text)
            mp3(audio, sr, f'{OUT}/ru{i}.{vid}.mp3')
            return {'id': vid, 'file': f'ru{i}.{vid}.mp3', 'sent': text}
        vs = [dict(render(vid, voice), label=label) for vid, label, voice in blind]
        sections.append({'id': f'ru{i}', 'title': f'Фраза {i + 1}: вслепую', 'multi_best': False, 'phrases': [
            {'id': f'ru{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
             'note': '★ лучший; ok — годится; ✗ — плохо (шум, металл, ошибки, монотонно)'}]})
        subprocess.run(['cp', f'out/st1/ru{i}.a.mp3', f'{OUT}/ru{i}.m1.mp3'], check=True)  # the M1 take rated in st1
        ref = [{'id': 'm1', 'label': 'M1 — учитель (Supertonic)', 'file': f'ru{i}.m1.mp3', 'sent': text}]
        ref += [dict(render(vid, voice), label=label) for vid, label, voice in old]
        sections.append({'id': f'old{i}', 'title': f'Фраза {i + 1}: OLD OLD OLD — для справки, не раунд', 'multi_best': True,
                         'phrases': [{'id': f'old{i}', 'text': text, 'ipa': '', 'script': '', 'variants': ref,
                                      'note': 'старые голоса Piper и учитель M1, подписаны открыто; оценивать не нужно'}]})
    json.dump({'round': 'stm1', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', [v[0] for v in blind])
