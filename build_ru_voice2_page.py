"""Blind A/B: the Russian voice v1 (on the site as dgru) vs v2 (training continued ~70 epochs, 1 h 35 min more).
Usage (on f3): .venv/bin/python build_ru_voice2_page.py /root/clone/ru-model /root/clone/ru-model2/out -> out/ruvoice2/, site/ruvoice2.html
"""
import json
import os
import random
import re
import sys
import time

from piper import PiperVoice

from build_ru_voice_page import LINES, render

OUT = 'out/ruvoice2'

if __name__ == '__main__':
    voices = {k: PiperVoice.load(f'{d}/ru_dg-medium.onnx', config_path=f'{d}/ru_dg-medium.onnx.json')
              for k, d in (('v1', sys.argv[1]), ('v2', sys.argv[2]))}
    os.makedirs(OUT, exist_ok=True)
    ver = int(time.time())
    phrases = []
    for n, text in enumerate(LINES):
        vs = []
        for k, v in voices.items():
            render(v, text, f'{OUT}/p{n}.{k}.mp3')
            vs.append({'id': k, 'label': {'v1': 'v1 (сейчас на сайте)', 'v2': 'v2 (дообучен)'}[k], 'src': f'audio/ruvoice2/p{n}.{k}.mp3?v={ver}'})
        random.Random(f'ruvoice2p{n}').shuffle(vs)  # blind
        for i, v in enumerate(vs):
            v['letter'] = chr(65 + i)
        phrases.append({'id': f'p{n}', 'text': text, 'note': '★ какой лучше, ✓ норм, ✗ плохо; нажми на слово с ошибкой',
                        'ipa': '', 'script': '', 'section': 'Русский', 'multi': False,
                        'words': re.findall(r'[^\s—–]+', text), 'variants': vs})
    page = open('page_template.html', encoding='utf-8').read()
    page = (page.replace('__TITLE__', 'Твой русский голос: v1 против v2')
            .replace('__INTRO__', 'Тот же голос, v2 дообучен ещё 1,5 часа. Вперемешку, вслепую. Если v2 не хуже — ставлю его на сайт.')
            .replace('__DATA__', json.dumps({'round': 'ruvoice2', 'phrases': phrases}, ensure_ascii=False)))
    open('site/ruvoice2.html', 'w', encoding='utf-8').write(page)
    print('ok', len(phrases))
