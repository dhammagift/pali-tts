"""Round 19: bitrate. The same synthesized audio encoded as the service does now (MP3 64 kbit/s) and
smaller (48, VBR ~40, 32 like Google), blind. Sibilants and aspirates first to suffer.
Usage: .venv/bin/python round19.py -> out/r19/*.mp3, out/r19/index.json
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from respell import en_phonemes

OUT = 'out/r19'
LENGTH = 1.15 / 0.875
ENC = [('a', 'MP3 64 кбит/с (сейчас)', ['-b:a', '64k']), ('b', 'MP3 48 кбит/с', ['-b:a', '48k']),
       ('c', 'MP3 VBR ~40 кбит/с', ['-q:a', '7']), ('d', 'MP3 32 кбит/с (как Google)', ['-b:a', '32k'])]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
alan = PiperVoice.load('models/en_GB-alan-medium.onnx')
os.makedirs(OUT, exist_ok=True)


def pali(t):
    return pratham.phoneme_ids_to_audio(pratham.phonemes_to_ids(list(tune(to_ipa(t, full_a=True)))),
                                        SynthesisConfig(length_scale=LENGTH, noise_scale=0.6, noise_w_scale=0.7))


def english(t):
    return alan.phoneme_ids_to_audio(alan.phonemes_to_ids(en_phonemes(alan, t)), SynthesisConfig(noise_scale=0.6, noise_w_scale=0.7))


ITEMS = [
    ('Cakkhusamphassapaccayā vedanā sukhā vā dukkhā vā adukkhamasukhā vā.', pali),
    ('Seyyathidaṁ, sammādiṭṭhi sammāsaṅkappo sammāvācā sammākammanto sammāājīvo sammāvāyāmo sammāsati sammāsamādhi.', pali),
    ('Passambhayaṁ kāyasaṅkhāraṁ assasissāmīti sikkhati.', pali),
    ('This is the sutta on the Dhamma: the Blessed One taught the bhikkhus this discourse.', english),
]
phrases = []
for n, (text, fn) in enumerate(ITEMS):
    pcm = fn(text).astype(np.float32)
    vs = []
    for vid, label, args in ENC:
        f = f'p{n}.{vid}.mp3'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                        *args, f'{OUT}/{f}'], input=pcm.tobytes(), check=True)
        vs.append({'id': vid, 'label': f'{label} · {os.path.getsize(f"{OUT}/{f}") // 1024} КБ', 'file': f, 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                    'note': '★ лучшее звучание; ✗ если слышно «бульканье», шипение или смазанные с/ш/кх'})
    print(n, flush=True)
json.dump({'round': 'r19', 'sections': [{'id': 'bitrate', 'title': 'Качество сжатия', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
