"""Round miles4 (owner 2026-10-19: «сравнение ... как было и как стало ему посмотреть»): Miles hears his voice as it was
in DG (from ryan, line ends cut), the 30 minutes from joe he accepted in miles3, and the 3 h from joe now live in DG
(en_miles2-medium), on miles3's lines plus two ordinary ones.
Usage (on f3): .venv/bin/python round_miles4.py -> out/miles4/; then build_page.py with ROUND = 'miles4', LANG = 'en'
"""
import json
import os

from piper import PiperVoice

from round_miles2 import read
from round_miles3 import TEXTS as TEXTS3
from round_st1 import mp3

OUT = 'out/miles4'
TEXTS = TEXTS3 + ['Mendicants, these two extremes should not be cultivated by one who has gone forth.',
                  'And what is that middle way of practice, realized by the Realized One, which gives vision and knowledge, '
                  'and leads to peace, direct knowledge, awakening, and extinguishment?']
VOICES = [('was', 'Before (endings cut)', 'models/en_miles-medium.onnx'),
          ('30m', '30 min test you accepted', '/root/en-miles/run5q/out/en_miles-medium.onnx'),
          ('now', 'Now in DG: 3 hours', 'models/en_miles2-medium.onnx')]

if __name__ == '__main__':
    voices = [(vid, label, PiperVoice.load(m, config_path=m + '.json')) for vid, label, m in VOICES]
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, label, voice in voices:
            f = f'en{i}.{vid}.mp3'
            mp3(*read(voice, text), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ best; ✓ ok; ✗ bad. Tap a word that is read wrong'})
    json.dump({'round': 'miles4', 'sections': [{'id': 'en', 'title': 'Yojanāni: before, 30 min, now',
                                                'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
