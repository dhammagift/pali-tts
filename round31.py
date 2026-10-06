"""Round 31: words before a comma come out broken in Memo (Kathañca, mahānāma, ...). The server splits only at
. ? ! ; : and leaves the comma as a pause symbol inside the chunk; pratham (a Hindi voice) swallows a final short a
before a pause - Google's Pali path in voice.js lengthened that a and dropped the comma for the same reason.
Variants, blind: a as now; b chunks cut at commas too, real silence between; c no comma at all; d b + the final
short a before a comma made long (Google's trick). Same settings as the site (length 1.15, noise 0.6/0.7).
Usage (on f3): .venv/bin/python round31.py -> out/r31/; then build_page.py with ROUND = 'r31'
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r31'
SENTENCE = re.compile(r'(?<=[.?!;:])\s+')
COMMA = re.compile(r'(?<=,)\s+')
SR = 22050
CFG = SynthesisConfig(length_scale=1.15, noise_scale=0.6, noise_w_scale=0.7)
TEXTS = [
    'Kathañca, mahānāma, ariyasāvako jāgariyaṁ anuyutto hoti?',
    'Idha, mahānāma, ariyasāvako divasaṁ caṅkamena nisajjāya āvaraṇīyehi dhammehi cittaṁ parisodheti,',
    'rattiyā paṭhamaṁ yāmaṁ caṅkamena nisajjāya āvaraṇīyehi dhammehi cittaṁ parisodheti,',
    'rattiyā majjhimaṁ yāmaṁ dakkhiṇena passena sīhaseyyaṁ kappeti, pāde pādaṁ accādhāya, sato sampajāno, uṭṭhānasaññaṁ manasi karitvā,',
    'rattiyā pacchimaṁ yāmaṁ paccuṭṭhāya caṅkamena nisajjāya āvaraṇīyehi dhammehi cittaṁ parisodheti.',
    'Evaṁ kho, mahānāma, ariyasāvako jāgariyaṁ anuyutto hoti.',
    'Kathañca, mahānāma, ariyasāvako sattahi saddhammehi samannāgato hoti?',
    'Idha, mahānāma, ariyasāvako saddho hoti, saddahati tathāgatassa bodhiṁ:',
    '‘itipi so bhagavā arahaṁ sammāsambuddho vijjācaraṇasampanno sugato lokavidū anuttaro purisadammasārathi satthā devamanussānaṁ buddho bhagavā’ti.',
    'Hirimā hoti, hirīyati kāyaduccaritena vacīduccaritena manoduccaritena, hirīyati pāpakānaṁ akusalānaṁ dhammānaṁ samāpattiyā.',
    'Ottappī hoti, ottappati kāyaduccaritena vacīduccaritena manoduccaritena, ottappati pāpakānaṁ akusalānaṁ dhammānaṁ samāpattiyā.',
    'Bahussuto hoti sutadharo sutasannicayo. Ye te dhammā ādikalyāṇā majjhekalyāṇā pariyosānakalyāṇā sātthā sabyañjanā kevalaparipuṇṇaṁ.',
]


def silence(sec):
    return np.zeros(int(SR * sec), dtype=np.float32)


def say(voice, ipa):
    ipa = ipa.strip(' ,')
    return voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), CFG) if ipa.strip(' ,.?!') else silence(0)


def render(voice, text, mode):
    parts = []
    for sent in SENTENCE.split(text.strip()):
        chunks = COMMA.split(sent) if mode in ('b', 'd') else [sent]
        for k, chunk in enumerate(chunks):
            ipa = tune(to_ipa(chunk, full_a=True))
            if mode == 'c':
                ipa = ipa.replace(',', '')
            if mode == 'd' and chunk.rstrip().endswith(','):
                ipa = re.sub(r'ʌ,?$', 'aː', ipa.rstrip())  # Google's trick: no swallowed final a before the pause
            parts += [say(voice, ipa), silence(0.25 if k < len(chunks) - 1 else 0.35)]
    return np.concatenate(parts)


if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    V = [('a', 'как сейчас (запятая — символ паузы внутри куска)'), ('b', 'резать и по запятым, между кусками тишина'),
         ('c', 'без запятой вовсе (без паузы)'), ('d', 'как b + конечное «а» перед запятой долгое (как у Google)')]
    phrases = []
    for n, text in enumerate(TEXTS):
        vs = []
        for vid, label in V:
            f = f'p{n}.{vid}.mp3'
            audio = render(voice, text, vid)
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            vs.append({'id': vid, 'label': label, 'file': f})
        phrases.append({'id': f'p{n}', 'text': text, 'ipa': tune(to_ipa(text, full_a=True)), 'script': '', 'variants': vs,
                        'note': '★ где слова перед запятой звучат целиком (Kathañca, mahānāma, Idha…)'})
    json.dump({'round': 'r31', 'sections': [{'id': 'p', 'title': 'Запятые (Memo, AN 7.67-подобный текст)', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
