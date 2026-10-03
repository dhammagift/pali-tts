"""Round 4: tune Piper pratham's own rules (not Google's) on single features.

Each phrase changes one thing in our IPA: single ñ, ññ, word-final ṁ, tempo.
Usage: .venv/bin/python round4.py  -> out/r4/*.mp3, out/r4/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa

OUT = 'out/r4'
v = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
END = r'(?=[ ,.?!]|$)'


def render(path, ipa, length=1.15):
    if os.path.exists(path):
        return
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)),
                                   SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-b:a', '64k', path], input=audio.astype(np.float32).tobytes(), check=True)


def phrase(pid, text, note, variants):
    """variants: (id, label, ipa transform, length_scale)."""
    base = to_ipa(text, full_a=True)
    vs = []
    for vid, label, fn, length in variants:
        ipa = fn(base)
        f = f'{OUT}/{pid}.{vid}.mp3'
        render(f, ipa, length)
        vs.append({'id': vid, 'label': label, 'file': os.path.basename(f), 'sent': ipa})
    print(pid)
    return {'id': pid, 'text': text, 'note': note, 'ipa': base, 'script': '', 'variants': vs}


SINGLE_N = r'(?<!ɲ)ɲ(?![ɲcɟ])'  # ñ alone (ñāṇa), not ññ and not ñc/ñj
os.makedirs(OUT, exist_ok=True)
items = [
    phrase('n1', 'Cakkhukaraṇī ñāṇakaraṇī upasamāya abhiññāya sambodhāya nibbānāya saṁvattati. Ñāyassa adhigamāya.',
           'SN 56.11, MN 10 · одиночное ñ (ñāṇa, ñāya): ★ где «нь», а не «н»',
           [(k, f'ñ как {r}', (lambda r: lambda s: re.sub(SINGLE_N, r, s))(r), 1.15)
            for k, r in [('nj0', 'ɲ'), ('nj1', 'nj'), ('nj2', 'ɲj'), ('nj3', 'nʲ')]]),
    phrase('n2', 'Rūpupādānakkhandho, vedanupādānakkhandho, saññupādānakkhandho, viññāṇupādānakkhandho. Paññā.',
           'SN 23.5 · ññ (saññā, viññāṇa, paññā): ★ где чёткое «ннь»',
           [(k, f'ññ как {r}', (lambda r: lambda s: s.replace('ɲɲ', r))(r), 1.15)
            for k, r in [('nn0', 'ɲɲ'), ('nn1', 'nɲ'), ('nn2', 'ɲː'), ('nn3', 'nnʲ')]]),
    phrase('m1', 'Evaṁ me sutaṁ. Paṭhamaṁ jhānaṁ upasampajja viharati. Seyyathidaṁ, sammādiṭṭhi.',
           'конечное ṁ: ★ где слышно «-нг» и слово не обрывается',
           [(k, f'конечное ṁ как {r}', (lambda r: lambda s: re.sub('ŋ' + END, r, s))(r), 1.15)
            for k, r in [('ng0', 'ŋ'), ('ng1', 'ŋː'), ('ng2', 'ŋɡ')]]),
    phrase('t1', 'Ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye. Tatra kho bhagavā pañcavaggiye bhikkhū āmantesi.',
           'SN 56.11 · темп: ★ самый естественный',
           [(k, f'темп ×{1 / l:.2f} (length_scale {l})', lambda s: s, l) for k, l in [('t0', 1.15), ('t1', 1.3), ('t2', 1.45)]]),
]
json.dump({'round': 'r4', 'sections': [{'id': 'piper', 'title': 'Piper pratham: свои правила', 'multi_best': False,
                                        'phrases': items}]},
          open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
