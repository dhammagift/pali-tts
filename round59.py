"""Round 59 (owner 2026-11-03, SN 35.28:1.1): pratham reads gayāyaṁ as «гее». Our phonemes are ɡʌjjˈaːjən (tune doubles
y between vowels): the model runs ʌjjaː together. gayāyaṁ and gayāsīse spelt four ways in the whole line: as it is /
one y / the stress on ga / ai before the y («гай-я»). 0.7x, one take each, blind.
Usage (on f3): .venv/bin/python round59.py -> out/r59/; then build_page.py with ROUND = 'r59'
"""
import json
import os
import subprocess

from round31 import SR
from round56 import ipa, synth

OUT = 'out/r59'
TEXT = 'Ekaṁ samayaṁ bhagavā gayāyaṁ viharati gayāsīse saddhiṁ bhikkhusahassena.'
LINE = ipa(TEXT)
WORDS = ('ɡʌjjˈaːjən', 'ɡʌjjaːsˈiːseː')
VARIANTS = [('a', 'как сейчас', WORDS),
            ('b', 'одно y', ('ɡʌjˈaːjən', 'ɡʌjaːsˈiːseː')),
            ('c', 'ударение на ga', ('ɡˈʌjjaːjən', 'ɡˈʌjjaːsiːseː')),
            ('d', 'ай перед y', ('ɡʌɪjˈaːjən', 'ɡʌɪjaːsˈiːseː'))]

if __name__ == '__main__':
    assert all(w in LINE for w in WORDS), LINE
    os.makedirs(OUT, exist_ok=True)
    vs = []
    for vid, label, (w1, w2) in VARIANTS:
        f = f'g.{vid}.mp3'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-q:a', '7', f'{OUT}/{f}'],
                       input=synth(LINE.replace(WORDS[0], w1).replace(WORDS[1], w2)).tobytes(), check=True)
        vs.append({'id': vid, 'label': label, 'file': f, 'sent': ''})
    phrases = [{'id': 'g', 'text': TEXT, 'ipa': '', 'script': '', 'variants': vs,
                'note': '★ лучше всех; ✓ правильно (гаяям, гаясисе); ✗ неправильно (что слышно)'}]
    json.dump({'round': 'r59', 'title': 'Pali TTS — раунд 59: gayāyaṁ',
               'intro': 'Pratham читает gayāyaṁ как «гее» (СН 35.28). Четыре варианта вслепую, 0.7x.',
               'sections': [{'id': 'g', 'title': 'gayāyaṁ, gayāsīse', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
