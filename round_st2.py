"""Supertonic 3, Russian: does it follow stress marks (a combining acute after the vowel, U+0301, which is in its
alphabet)? The same words with the stress on different syllables; ★ / ok where it is heard where it is marked.
Usage (on f3): .venv-ears/bin/python round_st2.py -> out/st2/; then build_page.py with ROUND = 'st2'
"""
import json
import os

from round_st1 import ST, mp3
from helper import load_text_to_speech, load_voice_style

OUT = 'out/st2'
A = '́'
SECTIONS = [
    ('homo', 'одинаковые слова, разное ударение', [f'Это старый за{A}мок.', f'Это старый замо{A}к.',
                                                   f'Он испытал му{A}ку.', f'Он купил муку{A}.']),
    ('names', 'имена и места пали с ударением', [f'Благословенный пребывал в Са{A}ваттхи.', f'Благословенный пребывал в Саваттхи{A}.',
                                                 f'Достопочтенный Сарипу{A}тта.', f'Достопочтенный Са{A}рипутта.',
                                                 f'В монастыре Анатхапи{A}ндики.', f'В монастыре Ана{A}тхапиндики.']),
    ('yo', 'буква ё', ['Всё ещё идёт дождь.', 'Он пришёл и принёс мёд.']),
]

if __name__ == '__main__':
    tts = load_text_to_speech(f'{ST}/assets/onnx')
    styles = {v: load_voice_style([f'{ST}/assets/voice_styles/{v}.json']) for v in ('M1', 'F1')}
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, texts in SECTIONS:
        phrases = []
        for i, text in enumerate(texts):
            vs = []
            for vid, v in (('a', 'M1'), ('b', 'F1')):
                f = f'{sid}{i}.{vid}.mp3'
                wav, dur = tts(text, 'ru', styles[v], 8, 1.05)
                mp3(wav.reshape(-1)[:int(tts.sample_rate * dur[0])], tts.sample_rate, f'{OUT}/{f}')
                vs.append({'id': vid, 'label': f'Supertonic 3 · {v}', 'file': f, 'sent': text})
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                            'note': '★ / ok где ударение там, где отмечено; ✗ где нет'})
        sections.append({'id': sid, 'title': title, 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'st2', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
