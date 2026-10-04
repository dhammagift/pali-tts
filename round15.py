"""Round 15: long vowels (ā ī ū e o), above all word-final ones, which pratham seems to read short
(bhikkhū, nadī, buddho, me, sattā). Variants on the IPA pratham gets now; the own voice as it is, for reference.
Usage: .venv/bin/python round15.py -> out/r15/*.mp3, out/r15/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r15'
LENGTH = 1.15 / 0.875  # the reader's default Pali pace (0.7)
TEXTS = [
    'Bhikkhavo ti. Bhadante ti te bhikkhū bhagavato paccassosuṁ.',
    'Natthi me saraṇaṁ aññaṁ, buddho me saraṇaṁ varaṁ.',
    'Idha bhikkhu vedanāsu vedanānupassī viharati ātāpī sampajāno satimā.',
    'Seyyathāpi nadī pabbateyyā dūraṅgamā sīghasotā hārahārinī.',
    'Sabbe sattā bhavantu sukhitattā. Aniccā vata saṅkhārā, uppādavayadhammino.',
]
LONG = r'([aiueo])ː'
END = r'(?=[ ,.?!]|$)'
VARIANTS = [  # id, label, transform of pratham's current IPA
    ('a', 'как сейчас (ː)', lambda s: s),
    ('b', 'конечные долгие с двойной долготой (ːː)', lambda s: re.sub(LONG + END, r'\1ːː', s)),
    ('c', 'все долгие с двойной долготой (ːː)', lambda s: re.sub(LONG, r'\1ːː', s)),
    ('d', 'конечные долгие как два звука (iː → iːi)', lambda s: re.sub(LONG + END, r'\1ː\1', s)),
]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
own = PiperVoice.load('models/pali_dg-medium.onnx')
os.makedirs(OUT, exist_ok=True)


def render(v, ipas, length, f):
    cfg = SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7)
    parts = []
    for ipa in ipas:
        parts += [v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), cfg), np.zeros(8000, dtype=np.float32)]
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-b:a', '64k', f],
                   input=np.concatenate(parts).tobytes(), check=True)


phrases = []
for n, text in enumerate(TEXTS):
    sents = [s for s in text.replace('. ', '.\n').split('\n') if s]
    base = [tune(to_ipa(s, full_a=True)) for s in sents]
    vs = []
    for vid, label, fn in VARIANTS:
        ipas = [fn(b) for b in base]
        render(pratham, ipas, LENGTH, f'{OUT}/p{n}.{vid}.mp3')
        vs.append({'id': vid, 'label': 'pratham: ' + label, 'file': f'p{n}.{vid}.mp3', 'sent': ' '.join(ipas)})
    render(own, [to_ipa(s, full_a=True) for s in sents], 1.0 / 0.875, f'{OUT}/p{n}.own.mp3')
    vs.append({'id': 'own', 'label': 'свой голос (как сейчас), для сравнения', 'file': f'p{n}.own.mp3', 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': ' '.join(base), 'script': '', 'variants': vs,
                    'note': '★ где долгие гласные (ā ī ū e o, особенно в конце слова) звучат долго и естественно; нажмите на слово, где долгая звучит коротко'})
    print(n, flush=True)
json.dump({'round': 'r15', 'sections': [{'id': 'long', 'title': 'Долгие гласные', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
