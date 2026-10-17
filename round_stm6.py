"""Round stm6: Puriso v2 on 8 lines of DG's own Russian translation (o; owner 2026-10-17: «включай переводы
правильные», not SC sv), none in M1's training clips; the owner clicks every wrong stress. Read by tts_server as DG
reads them (rules r49+).
Usage (on f3): /root/venv-ml/bin/python round_stm6.py [voice] -> out/stm6/; then build_page.py with ROUND = 'stm6'
"""
import json
import os
import sys

from round_st1 import piper

OUT = 'out/stm6'
VOICE = sys.argv[1] if len(sys.argv) > 1 else 'puriso'
TEXTS = [  # dg.db translator 'o': sn56.39:2.1, sn15.20:2.9, an4.160:9.2, sn45.161:1.6, sn35.230:4.1, sn56.59:1.3,
           # dn22:1.9, sn48.28:1.3
    'Это как если, монахи, лёгкий пучок хлопка или пучок каппасы ветром удерживаемый на ровный участок земли приземлившийся.',
    'Увидьте, монахи, и этой горы обозначение исчезло, и те люди умерли, и тот Благословенный достиг Париниббаны.',
    'Это, монахи, второе явление истиной Дхаммы к устойчивости, к незамутнению, к неисчезновению ведёт.',
    'И для этих, монахи, трёх поисков опознания (непосредственного знания) Благородный Восьмеричный Путь следует развить.',
    'И есть, монахи, глазом распознаваемые образы желанные, обожаемые, приятные, миловидные, с-желанием-связанные, очаровывающие.',
    'что больше—семь размером с горчичное зерно положенных каменных осколков или Гималаи царь гор”?',
    'Вот, монахи, монах в теле тело-наблюдающий пребывает, пылкий, сознательный, памятующий, выводя (вычищая) к миру-свету '
    'алчность-недовольство,',
    'Способность глаза, способность уха, способность носа, способность языка, способность ум-представления.']

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        f = f'ru{i}.{VOICE}.mp3'
        piper(text, VOICE, f'{OUT}/{f}')
        phrases.append({'id': f'ru{i}', 'text': text, 'ipa': '', 'script': '',
                        'variants': [{'id': VOICE, 'label': f'Puriso v2 ({VOICE})', 'file': f, 'sent': text}],
                        'note': 'кликни каждое слово с неправильным ударением или произношением; ✓ норм — если всё верно'})
    json.dump({'round': 'stm6', 'sections': [{'id': 'ru', 'title': 'Puriso: ударения на переводах o', 'multi_best': True,
                                              'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
