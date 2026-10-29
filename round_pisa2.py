"""Round pisa2 (owner 2026-10-29: try pali_sa again, after ElevenLabs failed on Pali): pali_sa (pratham's timbre, Sanskrit
reading via Indic Parler + kNN-VC; pisa1: ok 8 bad 3, pratham ok 5 bad 4) against pratham as in DG (0.7x), on el2's
16 lines - the ones the old rounds kept failing on. pali_sa at length 1.05 (its pace = pratham at 0.7x, as pisa1). Blind.
Usage (on f3): .venv/bin/python round_pisa2.py -> out/pisa2/; then build_page.py with ROUND = 'pisa2'
"""
import json
import os

from piper import PiperVoice

from round_el2 import TEXTS
from round_pisa1 import SA, pali_sa, pratham

OUT = 'out/pisa2'

if __name__ == '__main__':
    voice = PiperVoice.load(SA, config_path=SA + '.json')
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, (text, why) in enumerate(TEXTS):
        vs = []
        for name, mp3 in (('pratham', pratham(text)), ('pali_sa', pali_sa(voice, text, 1.05))):
            f = f'p{i:02d}.{name}.mp3'
            open(f'{OUT}/{f}', 'wb').write(mp3)
            vs.append({'id': name, 'label': name, 'file': f, 'sent': ''})
        phrases.append({'id': f'p{i:02d}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'Было: {why}. ★ лучший; ✓ правильно; ✗ неправильно. На слово с ошибкой можно нажать'})
    json.dump({'round': 'pisa2', 'title': 'pali_sa на нерешённых местах',
               'intro': 'Тембр pratham, выговор санскритского диктора (pali_sa) против pratham, как сейчас в DG (0.7x). '
                        'Фразы — те, на которых спотыкались старые раунды. Вслепую.',
               'sections': [{'id': 'p', 'title': 'Пали: нерешённые места', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
