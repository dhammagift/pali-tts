"""Round 57 (round 56: «…cittāni vimucciṁsūti.» bad in all three takes, «чиксути», owner: «вимучи-m-сути»): the word itself
spelt otherwise, all with ṁ as m (the owner hears an m): cc as it is / single c / a pause before it / ti apart.
0.7x, one take each, blind. Usage (on f3): .venv/bin/python round57.py -> out/r57/; then build_page.py with ROUND = 'r57'
"""
import json
import os
import subprocess

from round31 import SR
from round56 import VIM, synth

OUT = 'out/r57'
WORD = 'ʋɪmʊccɪŋsˈuːtɪ'
assert WORD in VIM, VIM
VARIANTS = [('a', 'ṁ как m', 'ʋɪmʊccɪmsˈuːtɪ'),
            ('b', 'ṁ как m, одно c', 'ʋɪmʊcɪmsˈuːtɪ'),
            ('c', 'ṁ как m, пауза перед словом', ', ʋɪmʊccɪmsˈuːtɪ'),
            ('d', 'ṁ как m, ti отдельно', 'ʋɪmʊccɪmsˈuː tɪ')]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    vs = []
    for vid, label, spelt in VARIANTS:
        f = f'v.{vid}.mp3'
        ipa = VIM.replace(' ' + WORD, spelt if spelt.startswith(',') else ' ' + spelt)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-q:a', '7', f'{OUT}/{f}'], input=synth(ipa).tobytes(), check=True)
        vs.append({'id': vid, 'label': label, 'file': f, 'sent': ''})
    phrases = [{'id': 'v', 'text': 'Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.',
                'ipa': '', 'script': '', 'variants': vs, 'note': '★ лучше всех; ✓ правильно; ✗ неправильно (что слышно)'}]
    json.dump({'round': 'r57', 'sections': [{'id': 'p', 'title': 'vimucciṁsūti, 0.7x', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(vs))
