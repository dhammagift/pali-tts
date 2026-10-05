"""espeak-ng `pi`, es5 note on viññāṇa: "the retroflex sounds somehow wrong". espeak has one retroflex n for every
Indic language (base n.), so the choice is that or a plain n. Blind.
Usage: python3 round_es7.py -> out/es7/; then build_page.py with ROUND = 'es7'
"""
import json
import os
import subprocess

from round_es3 import BIN, ENV, phonemes

OUT = 'out/es7'
TEXTS = ['viññāṇa', 'ñāṇadassana', 'Jarāmaraṇaṁ sokaparidevadukkhadomanassupāyāsā.', 'kāraṇa', 'brāhmaṇa',
         'Saṅkhārapaccayā viññāṇaṁ, viññāṇapaccayā nāmarūpaṁ.']
VARIANTS = [('a', 'сейчас: ретрофлексная ṇ', lambda s: s), ('b', 'обычная n', lambda s: s.replace('n.', 'n'))]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for n, text in enumerate(TEXTS):
        clauses = [c.strip() for c in phonemes(text).splitlines() if c.strip()]
        vs = []
        for vid, label, fn in VARIANTS:
            ph = [fn(c) for c in clauses]
            assert vid == 'a' or ph != clauses, text
            wav = subprocess.run([BIN, '-v', 'pi', '-s', '140', '--stdout', ' '.join(f'[[{c}]],' for c in ph)], env=ENV,
                                 capture_output=True, check=True).stdout
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-ac', '1', '-q:a', '6', f'{OUT}/p{n}.{vid}.mp3'], input=wav, check=True)
            vs.append({'id': vid, 'label': label, 'file': f'p{n}.{vid}.mp3'})
        phrases.append({'id': f'p{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs, 'note': '★ где ṇ звучит правильно'})
    json.dump({'round': 'es7', 'sections': [{'id': 'n', 'title': 'espeak: ṇ', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
