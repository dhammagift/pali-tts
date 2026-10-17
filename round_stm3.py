"""Round stm3 (owner 2026-10-16: «сделай мини раунд»): the M1 student (stm1a) alone on 8 ordinary SuttaCentral lines,
read as DG reads them (tts_server, rules r43+); the owner clicks every word with a wrong stress. The same lines go to
the student retrained on M1's stress-marked clips, so the two error lists compare.
Usage (on f3): /root/venv-ml/bin/python round_stm3.py [voice] -> out/stm3/; then build_page.py with ROUND = 'stm3'
"""
import json
import os
import sys

from round_st1 import piper

OUT = 'out/stm3'
VOICE = sys.argv[1] if len(sys.argv) > 1 else 'puriso'
TEXTS = ['Так я слышал. Однажды Благословенный проживал в стране Куру, где был город под названием Каммасадхамма.',
         'Не склоняясь ни к одной из этих крайностей, Татхагата пробудился в срединный путь, который способствует '
         'видению, который способствует знанию, который ведёт к покою, к прямому знанию, к просветлению, к ниббане.',
         'Вот, монахи, монах пребывает в созерцании тела как тела, будучи решительным, бдительным, осознанным, '
         'устранив алчность и грусть к миру.',
         'Каков будет его будущий удел? Каково его будущее направление?',
         'Поскольку он считает всё это таковым, он не волнуется о том, чего не существует.',
         'Таково пятое знание, обретённое им, благородное, сверхмирское, которого не имеют обычные заурядные люди.',
         '«Точно так же, Маханама, благородный ученик, наделённый этими четырьмя вещами, склоняется, устремляется, '
         'направляется к ниббане».',
         'По мере того как он ходил от дома к дому в Саваттхи, собирая подаяния, он увидел некую женщину в родовых '
         'муках, с болезненными родами.']

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        f = f'ru{i}.{VOICE}.mp3'
        piper(text, VOICE, f'{OUT}/{f}')
        phrases.append({'id': f'ru{i}', 'text': text, 'ipa': '', 'script': '',
                        'variants': [{'id': VOICE, 'label': f'ученик M1 ({VOICE})', 'file': f, 'sent': text}],
                        'note': 'кликни каждое слово с неправильным ударением или произношением; ✓ норм — если всё верно'})
    json.dump({'round': 'stm3', 'sections': [{'id': 'ru', 'title': 'Ученик M1: ударения', 'multi_best': True,
                                              'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
