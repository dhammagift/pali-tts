"""Stress check for the Russian voice: the sentences with the owner's marked words (ruvoice1/2), espeak's stress
vs respell.RU_STRESS. Usage (on f3): .venv/bin/python build_ru_stress_page.py -> out/rustress1/, site/rustress1.html
"""
import json
import os
import re
import time

from piper import PiperVoice

import respell
from build_ru_voice_page import LINES, render

OUT = 'out/rustress1'

if __name__ == '__main__':
    voice = PiperVoice.load('models/ru_dg2-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    ver = int(time.time())
    phrases = []
    fix = dict(respell.RU_STRESS)
    for n, text in ((2, LINES[2]), (5, LINES[5])):
        vs = []
        for k, label in (('old', 'как сейчас (ударения espeak)'), ('new', 'с исправленными ударениями')):
            respell.RU_STRESS.clear()
            if k == 'new':
                respell.RU_STRESS.update(fix)
            render(voice, text, f'{OUT}/p{n}.{k}.mp3')
            vs.append({'id': k, 'letter': label, 'label': '', 'src': f'audio/rustress1/p{n}.{k}.mp3?v={ver}'})
        phrases.append({'id': f'p{n}', 'text': text, 'note': 'Варана́си, Исипата́не', 'ipa': '', 'script': '',
                        'section': 'Ударения', 'multi': True, 'words': re.findall(r'[^\s—–]+', text), 'variants': vs})
    page = open('page_template.html', encoding='utf-8').read()
    page = (page.replace('__TITLE__', 'Русский голос: ударения')
            .replace('__INTRO__', 'Варана́си и Исипата́не: как сейчас и исправленные. Если «исправленные» верно — включаю на сайте.')
            .replace('__DATA__', json.dumps({'round': 'rustress1', 'phrases': phrases}, ensure_ascii=False)))
    open('site/rustress1.html', 'w', encoding='utf-8').write(page)
    print('ok', len(phrases))
