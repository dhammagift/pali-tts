"""Round 59 (owner 2026-11-03, SN 35.28:1.1): pratham read gayāyaṁ as «гее» - the short a before y melts into e (Hindi
ay), as dhārayāmīti in rounds 50/52. Four spellings by ear were all bad (owner); then the phoneme recogniser
(wav2vec2-lv-60-espeak) picked the open a with one j, «гай-» in 8 of 8 takes (as it is 0 of 8): now the rule after g.
Only the new reading, on the two lines where the word stands. 0.7x.
Usage (on f3): .venv/bin/python round59.py -> out/r59/; then build_page.py with ROUND = 'r59'
"""
import json
import os
import shutil
import subprocess

from round31 import SR
from round56 import ipa, synth

OUT = 'out/r59'
LINES = [('sn', 'Ekaṁ samayaṁ bhagavā gayāyaṁ viharati gayāsīse saddhiṁ bhikkhusahassena.'),
         ('th', 'Itthaṁ sudaṁ āyasmā gayākassapo thero imā gāthāyo abhāsitthāti.')]

if __name__ == '__main__':
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    phrases = []
    for pid, text in LINES:
        f = f'{pid}.a.mp3'
        assert 'ɡaj' in ipa(text), ipa(text)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-q:a', '7', f'{OUT}/{f}'], input=synth(ipa(text)).tobytes(), check=True)
        phrases.append({'id': pid, 'text': text, 'ipa': '', 'script': '', 'note': '✓ правильно (гаяям, гаясисе, гаякассапо); ✗ неправильно (что слышно)',
                        'variants': [{'id': 'a', 'label': 'новое правило', 'file': f, 'sent': ''}]})
    json.dump({'round': 'r59', 'title': 'Pali TTS — раунд 59: gayāyaṁ',
               'intro': 'Pratham читал gayāyaṁ как «гее» (СН 35.28). Новое правило, проверено распознавателем; 0.7x.',
               'sections': [{'id': 'g', 'title': 'gayā-', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
