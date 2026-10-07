"""Listening page for the trained Russian voice (Piper fine-tuned from ruslan on the clone's dataset, kaggle-ru-train):
the new voice, ruslan (the site's voice now) and, where it exists, the Chatterbox clone itself (clone1), names shown.
Usage (on f3): .venv/bin/python build_ru_voice_page.py /root/clone/ru-model -> out/ruvoice1/, site/ruvoice1.html
"""
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
from piper import PiperVoice, SynthesisConfig

from respell import ru_phonemes

OUT = 'out/ruvoice1'
LINES = ['Это, монахи, боль благородно-истина.',
         'И с запущенным колесом Учения о действительности местные божества провозгласили.',
         'Вот Благословенным в Варанаси, в Исипатане, в Оленьем Парке запущено колесо непревзойдённого Учения.',
         'И что такое, монахи, боль? Та которая, монахи, телесная боль, телесный дискомфорт, это называется, монахи, боль.',
         'Татхагата, ниббана, дхамма, сангха.',
         'Одно время Благословенный в Варанаси располагается, в Исипатане, в Оленьем Парке.',
         'День, кровь, жизнь, только учитель.',
         'Монахи, когда Кассапа посещает семьи, его ум не застревает, не сдерживается, не связывается в семьях.']
CFG = SynthesisConfig(noise_scale=0.6, noise_w_scale=0.7)


def render(voice, text, f):
    audio = np.concatenate([np.concatenate([voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph), CFG),
                                            np.zeros(int(22050 * 0.35), np.float32)]) for ph in ru_phonemes(voice, text)])
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-q:a', '6', f], input=audio.astype(np.float32).tobytes(), check=True)


if __name__ == '__main__':
    MODEL = sys.argv[1]
    new = PiperVoice.load(f'{MODEL}/ru_dg-medium.onnx', config_path=f'{MODEL}/ru_dg-medium.onnx.json')
    ruslan = PiperVoice.load('models/ru_RU-ruslan-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    ver = int(time.time())
    phrases = []
    for n, text in enumerate(LINES):
        render(new, text, f'{OUT}/p{n}.new.mp3')
        render(ruslan, text, f'{OUT}/p{n}.ruslan.mp3')
        vs = [{'id': 'new', 'letter': 'новый голос (Piper, твой тембр)', 'label': 'дообучен с ruslan на 1 ч клона',
               'src': f'audio/ruvoice1/p{n}.new.mp3?v={ver}'},
              {'id': 'ruslan', 'letter': 'ruslan (сейчас на сайте)', 'label': 'для сравнения',
               'src': f'audio/ruvoice1/p{n}.ruslan.mp3?v={ver}'}]
        if n < 5 and os.path.exists(f'out/clone1/ru{n}.1.mp3'):
            vs.append({'id': 'clone', 'letter': 'клон Chatterbox (учитель)', 'label': 'большая модель, только на видеокарте',
                       'src': f'audio/clone1/ru{n}.1.mp3?v={ver}'})
        phrases.append({'id': f'p{n}', 'text': text, 'note': '★ нравится (можно несколько), ✓ норм, ✗ плохо; нажми на слово с ошибкой',
                        'ipa': '', 'script': '', 'section': 'Русский', 'multi': True,
                        'words': re.findall(r'[^\s—–]+', text), 'variants': vs})
    page = open('page_template.html', encoding='utf-8').read()
    page = (page.replace('__TITLE__', 'Твой русский голос: первая версия')
            .replace('__INTRO__', 'Быстрый голос Piper (ONNX, как ruslan), дообученный 7 часов на 790 фразах, которые начитал клон твоего голоса. Ударения — по словарю espeak, как у ruslan. Сравни с ruslan и с самим клоном.')
            .replace('__DATA__', json.dumps({'round': 'ruvoice1', 'phrases': phrases}, ensure_ascii=False)))
    open('site/ruvoice1.html', 'w', encoding='utf-8').write(page)
    print('ok', len(phrases))
