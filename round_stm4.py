"""Round stm4 (owner 2026-10-16: before any GPU goes to the student, hear how M1 reads with our stress marks - that is
what the retrained student would learn): Supertonic M1 on stm3's 8 lines with respell.ru_stress_marks (rules r44+),
as gen_supertonic_ru.py reads the training clips. The owner clicks every wrong stress; few -> the student retrains.
Usage (on f3): .venv/bin/python round_stm4.py -> out/stm4/; then build_page.py with ROUND = 'stm4'
"""
import json
import os

from piper import PiperVoice

from respell import ru_stress_marks
from round_st1 import ST, load_text_to_speech, load_voice_style, mp3
from round_stm3 import TEXTS

OUT = 'out/stm4'

if __name__ == '__main__':
    marker = PiperVoice.load('models/ru_RU-ruslan-medium.onnx')
    tts = load_text_to_speech(f'{ST}/assets/onnx')
    m1 = load_voice_style([f'{ST}/assets/voice_styles/M1.json'])
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        wav, dur = tts(ru_stress_marks(marker, text), 'ru', m1, 8, 1.05)
        f = f'ru{i}.m1s.mp3'
        mp3(wav.reshape(-1)[:int(tts.sample_rate * dur[0])], tts.sample_rate, f'{OUT}/{f}')
        phrases.append({'id': f'ru{i}', 'text': text, 'ipa': '', 'script': '',
                        'variants': [{'id': 'm1s', 'label': 'M1 со знаками ударения', 'file': f, 'sent': text}],
                        'note': 'кликни каждое слово с неправильным ударением или произношением; ✓ норм — если всё верно'})
    json.dump({'round': 'stm4', 'sections': [{'id': 'ru', 'title': 'Как переобученный ученик будет ставить ударения',
                                              'multi_best': True, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
