"""Round en1: the first fixes from the DG voice sheet (yojanani sara DG, owner + Miles, 2026-10-17), each in a Sujato
line, read by every English DG voice (labelled, not blind): phenomena (not "penomna"), Buddha (BUD-da), live (liv).
Usage (on f3): /root/venv-ml/bin/python round_en1.py -> out/en1/; then build_page.py with ROUND = 'en1'
"""
import json
import os

from round_st1 import piper

OUT = 'out/en1'
TEXTS = [('phenomena', '‘So it seems that these phenomena, not having been, come to be; and having come to be, they flit away.’'),
         ('Buddha', 'When he said this, one of the mendicants said to the Buddha,'),
         ('live', '‘Think like this, not like that. Focus your mind like this, not like that. Give up this, and live having '
                  'achieved that.’')]
VOICES = [('miles', 'Yojanāni'), ('alan', 'Alan'), ('kathleen', 'Kathleen')]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, (word, text) in enumerate(TEXTS):
        vs = []
        for vid, label in VOICES:
            f = f'en{i}.{vid}.mp3'
            piper(text, vid, f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'исправлено: {word}. ✓ норм — если теперь верно; слово с ошибкой — кликни'})
    json.dump({'round': 'en1', 'sections': [{'id': 'en', 'title': 'Исправления из таблицы', 'multi_best': True,
                                             'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
