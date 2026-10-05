"""Round 23: stability. VITS samples noise on every call (noise_scale, noise_w), so a fixed rule can still
lose a syllable in one take of two (jarāpi -> 'japi' even with round 22's fix). Same r20 phonemes at
three noise levels, three takes each: does less noise keep every syllable?
Usage: .venv/bin/python round23.py -> out/r23/*.mp3, out/r23/index.json
"""
import json
import os
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r23'
LENGTH = 1.15 / 0.875
TEXTS = [
    'Jarāpi dukkhā, maraṇampi dukkhaṁ.',
    'Paṭhamaṁ jhānaṁ upasampajja viharati.',
    'Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.',
    'Nimmānaratī devā saddamanussāvesuṁ.',
]
LEVELS = [('a', 'как сейчас (noise 0.6 / 0.7)', 0.6, 0.7),
          ('b', 'меньше случайности (0.33 / 0.5)', 0.333, 0.5),
          ('c', 'минимум случайности (0.15 / 0.3)', 0.15, 0.3)]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
os.makedirs(OUT, exist_ok=True)
phrases = []
for n, text in enumerate(TEXTS):
    ipa = tune(to_ipa(text, full_a=True))
    vs = []
    for vid, label, ns, nw in LEVELS:
        for take in (1, 2, 3):
            f = f'p{n}.{vid}{take}.mp3'
            audio = pratham.phoneme_ids_to_audio(pratham.phonemes_to_ids(list(ipa)), SynthesisConfig(length_scale=LENGTH, noise_scale=ns, noise_w_scale=nw))
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                            '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-q:a', '7', f'{OUT}/{f}'], input=audio.tobytes(), check=True)
            vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': ipa})
    phrases.append({'id': f'p{n}', 'text': text, 'ipa': ipa, 'script': '', 'variants': vs,
                    'note': '✓ если все слоги на месте (jarāpi, paṭhamaṁ…), ✗ если что-то проглочено; ★ самый естественный'})
    print(n, flush=True)
json.dump({'round': 'r23', 'sections': [{'id': 'noise', 'title': 'Стабильность: уровень случайности синтеза', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
