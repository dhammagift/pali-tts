"""Listening page for the owner's voice cloned by Chatterbox Multilingual (Kaggle job dg-clone, reference: 18 s of the
owner reading SN 56.11), 2 takes per line, next to the voices DG has now (ruslan / alan) and the reference itself.
Names shown. Run on f3 after the job: python3 build_clone.py /root/clone/out/out -> out/clone1/, site/clone1.html
"""
import base64
import json
import os
import re
import shutil
import sys
import time
import urllib.request

SRC = sys.argv[1]
OUT = 'out/clone1'
LINES = {
    'ru': ['Это, монахи, боль благородно-истина.',
           'И с запущенным колесом Учения о действительности местные божества провозгласили.',
           'Вот Благословенным в Варанаси, в Исипатане, в Оленьем Парке запущено колесо непревзойдённого Учения.',
           'И что такое, монахи, боль? Та которая, монахи, телесная боль, телесный дискомфорт, это называется, монахи, боль.',
           'Татхагата, ниббана, дхамма, сангха.'],
    'en': ['At one time the Buddha was staying near Varanasi in the deer park at Isipatana.',
           'There the Buddha addressed the group of five mendicants.',
           'And when the Buddha rolled forth the Wheel of Dhamma, the earth gods raised the cry.',
           'In brief, the five grasping aggregates are suffering.'],
}
NOW = {'ru': 'ruslan', 'en': 'alan'}


def synth(text, voice, f):
    req = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': voice}).encode(),
                                 {'content-type': 'application/json'})
    open(f, 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(req))['audioContent']))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    ver = int(time.time())
    phrases = []
    for lang, lines in LINES.items():
        for n, text in enumerate(lines):
            vs = []
            for take in (1, 2):
                f = f'{lang}{n}.{take}.mp3'
                shutil.copy(os.path.join(SRC, f), f'{OUT}/{f}')
                vs.append({'id': f'c{take}', 'letter': f'клон · дубль {take}', 'label': 'Chatterbox, твой голос по образцу 18 с',
                           'src': f'audio/clone1/{f}?v={ver}'})
            synth(text, NOW[lang], f'{OUT}/{lang}{n}.now.mp3')
            vs.append({'id': 'now', 'letter': f'сейчас на сайте: {NOW[lang]}', 'label': 'для сравнения',
                       'src': f'audio/clone1/{lang}{n}.now.mp3?v={ver}'})
            phrases.append({'id': f'{lang}{n}', 'text': text, 'note': '★ нравится (можно несколько), ✓ норм, ✗ плохо',
                            'ipa': '', 'script': '', 'section': 'Русский' if lang == 'ru' else 'English', 'multi': True,
                            'words': re.findall(r'[^\s—–]+', text), 'variants': vs})
    page = open('page_template.html', encoding='utf-8').read()
    page = (page.replace('__TITLE__', 'Твой голос: клон (Chatterbox)')
            .replace('__INTRO__', 'Chatterbox Multilingual (открытая, MIT) прочитал фразы твоим голосом по 18-секундному куску твоей записи SN 56.11, без обучения. Если клон устроит, им начитаем 1–2 часа и дообучим из этого быстрый голос Piper (ONNX), как ruslan. Оценивай похожесть на тебя и правильность чтения.')
            .replace('__DATA__', json.dumps({'round': 'clone1', 'phrases': phrases}, ensure_ascii=False)))
    open('site/clone1.html', 'w', encoding='utf-8').write(page)
    print('ok', len(phrases))
