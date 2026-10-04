"""Round 22: the open-a rule (round 9: unstressed medial ʌ -> a, for 'viharati' read as 'viharti').
Nearly every word the owner later heard swallowed has that a in it (jarāpi, passambhayaṁ, ponobbhavikā,
taṇhāya, nimmānaratī, paṭhamaṁ...). Same phrases with the rule on (now) and off, two takes each.
Usage: .venv/bin/python round22.py -> out/r22/*.mp3, out/r22/index.json
"""
import json
import os
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import MONO_HIATUS, PRATHAM_RULES, to_ipa, tune

OUT = 'out/r22'
LENGTH = 1.15 / 0.875
TEXTS = [
    'Paṭhamaṁ jhānaṁ upasampajja viharati.',
    'Jarāpi dukkhā, maraṇampi dukkhaṁ.',
    'Passambhayaṁ kāyasaṅkhāraṁ assasissāmīti sikkhati.',
    'Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.',
    'Taṇhāya nirodhā upādānanirodho.',
    'Evaṁ tiparivaṭṭaṁ dvādasākāraṁ yathābhūtaṁ ñāṇadassanaṁ.',
    'Nimmānaratī devā saddamanussāvesuṁ.',
    'Ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.',
]


def without_open_a(text):
    ipa = to_ipa(text, full_a=True)
    for i, (rx, rep) in enumerate(PRATHAM_RULES):
        if i != 3:  # 3 = round 9's open-a rule
            ipa = rx.sub(rep, ipa)
    return MONO_HIATUS.sub(r'\1, ', ipa)


VARIANTS = [('a', 'как сейчас (с «открытым а»)', lambda t: tune(to_ipa(t, full_a=True))),
            ('b', 'без правила «открытого а»', without_open_a)]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
os.makedirs(OUT, exist_ok=True)
phrases = []
for n, text in enumerate(TEXTS):
    vs = []
    for vid, label, fn in VARIANTS:
        ipa = fn(text)
        for take in (1, 2):
            f = f'p{n}.{vid}{take}.mp3'
            audio = pratham.phoneme_ids_to_audio(pratham.phonemes_to_ids(list(ipa)), SynthesisConfig(length_scale=LENGTH, noise_scale=0.6, noise_w_scale=0.7))
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                            '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-q:a', '7', f'{OUT}/{f}'], input=audio.tobytes(), check=True)
            vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': ipa})
    assert vs[0]['sent'] != vs[2]['sent'], text
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': vs[0]['sent'], 'script': '', 'variants': vs,
                    'note': '★ где все слоги на месте (jarāpi, paṭhamaṁ, viharati…); ✗ где слог проглочен'})
    print(n, flush=True)
json.dump({'round': 'r22', 'sections': [{'id': 'opena', 'title': 'Правило «открытого а»: с ним и без', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
