"""Round miles7 (owner 2026-10-23: Miles's 300 takes, ~20 min, are too little for Piper): Yojanāni v3 - ryan read 2600
Sujato sentences, kNN-VC turned them into Miles's timbre, Piper from ryan on those + his own takes (kaggle-en-miles-vc,
4 h) - against the voice now in DG (v1, round miles5). Both with the tail that saves a line's last sound. Blind, for
Miles; miles4's lines plus two «by» lines (SN 12.2, DG's own translation).
Usage (on f3): .venv/bin/python round_miles7.py -> out/miles7/; then build_page.py with ROUND = 'miles7', LANG = 'en'
"""
import json
import os

from piper import PiperVoice

from round_miles4 import TEXTS as TEXTS4
from round_miles5 import V1, align, read_carried
from round_st1 import mp3

OUT = 'out/miles7'
V3 = 'models/en_miles3-medium.onnx'
TEXTS = TEXTS4 + ['by attention conditioned is name-matter;', 'by name-matter conditioned is the six-fold area;']

if __name__ == '__main__':
    voices = [(name, PiperVoice.load(m, config_path=m + '.json'), align(m)) for name, m in (('v1', V1), ('v3', V3))]
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, (name, voice, sess) in zip('ab', voices if i % 2 == 0 else voices[::-1]):  # blind: A is not always v1
            f = f'en{i}.{vid}.mp3'
            mp3(*read_carried(voice, sess, text), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': vid.upper(), 'voice': name, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ best; ✓ ok; ✗ bad. Which sounds more like you, and clearer? Tap a word that is read wrong'})
    json.dump({'round': 'miles7', 'sections': [{'id': 'en', 'title': 'Yojanāni: which sounds better?', 'multi_best': False,
                                                'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
