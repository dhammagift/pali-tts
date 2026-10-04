"""Round 20: ṭṭh ('sammādiṭṭhi' read as 'самма дичи': the geminate aspirated retroflex comes out as an
affricate). Pratham: as now ʈʈʰ / single ʈʰ / long ʈːʰ / unaspirated ʈʈ / dental ttʰ; two takes each.
Own voice for reference.
Usage: .venv/bin/python round20.py -> out/r20/*.mp3, out/r20/index.json
"""
import json
import os
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r20'
LENGTH = 1.15 / 0.875
TEXTS = [
    'Sammādiṭṭhi sammāsaṅkappo.',
    'Ayameva ariyo aṭṭhaṅgiko maggo.',
    'Diṭṭheva dhamme sukhavihārī; seṭṭho so tiṭṭhati.',
    'Atthi imasmiṁ kāye aṭṭhi aṭṭhimiñjaṁ.',
]
VARIANTS = [
    ('a', 'как сейчас (ʈʈʰ)', lambda s: s),
    ('b', 'одно ʈʰ (без удвоения)', lambda s: s.replace('ʈʈʰ', 'ʈʰ')),
    ('c', 'долгое ʈːʰ', lambda s: s.replace('ʈʈʰ', 'ʈːʰ')),
    ('d', 'без придыхания ʈʈ', lambda s: s.replace('ʈʈʰ', 'ʈʈ')),
    ('e', 'зубное ttʰ', lambda s: s.replace('ʈʈʰ', 'ttʰ')),
]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
own = PiperVoice.load('models/pali_dg-medium.onnx')
os.makedirs(OUT, exist_ok=True)


def render(v, ipa, length, f):
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-q:a', '7', f], input=audio.tobytes(), check=True)


phrases = []
for n, text in enumerate(TEXTS):
    base = tune(to_ipa(text, full_a=True))
    vs = []
    for vid, label, fn in VARIANTS:
        for take in (1, 2):
            f = f'p{n}.{vid}{take}.mp3'
            render(pratham, fn(base), LENGTH, f'{OUT}/{f}')
            vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': fn(base)})
    render(own, to_ipa(text, full_a=True), 1.0 / 0.875, f'{OUT}/p{n}.own.mp3')
    vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'p{n}.own.mp3', 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': base, 'script': '', 'variants': vs,
                    'note': '★ где ṭṭh (diṭṭhi, aṭṭhi) звучит как «тх», а не «ч»'})
    print(n, flush=True)
json.dump({'round': 'r20', 'sections': [{'id': 'tth', 'title': 'ṭṭh: «дичи» вместо «диттхи»', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
