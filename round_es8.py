"""espeak-ng `pi`: v in espeak's own voice. The ears hear a nasal (m/n) where espeak says v in 141 clips of es1/es5
- the "ма вместо ва" of es1 - while Piper voices on the same phonemes don't. ~12 words with v in every position;
current (Russian v) vs base v, Hindi ʋ, Italian v (temporary phonemes vb/vh/vi in ph_pali). Blind.
Usage: python3 round_es8.py -> out/es8/; then build_page.py with ROUND = 'es8'
"""
import json
import os
import subprocess

from round_es3 import BIN, ENV, phonemes

OUT = 'out/es8'
TEXTS = ['samaṇena vā brāhmaṇena vā devena vā', 'Ekaṁ samayaṁ bhagavā', 'āvuso', 'vedanā', 'viññāṇa',
         'Evaṁ me sutaṁ', 'saddamanussāvesuṁ', 'avijjā', 'bhavataṇhā, vibhavataṇhā', 'sammāvāyāmo sammāvācā',
         'Dveme, bhikkhave, antā', 'vihāra']
VARIANTS = [('a', 'сейчас: русская в', 'v'), ('b', 'обычная v (base)', 'vb'), ('c', 'хинди ʋ (было в es1)', 'vh'),
            ('d', 'итальянская v', 'vi')]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for n, text in enumerate(TEXTS):
        clauses = [c.strip() for c in phonemes(text).splitlines() if c.strip()]
        assert any('v' in c for c in clauses), text
        vs = []
        for vid, label, rep in VARIANTS:
            ph = ' '.join(f'[[{c.replace("v", rep)}]],' for c in clauses)
            wav = subprocess.run([BIN, '-v', 'pi', '-s', '140', '--stdout', ph], env=ENV, capture_output=True, check=True).stdout
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-ac', '1', '-q:a', '6', f'{OUT}/p{n}.{vid}.mp3'], input=wav, check=True)
            ipa = subprocess.run([BIN, '-q', '--ipa', '-v', 'pi', text], env=ENV, capture_output=True, text=True).stdout.replace('\n', ' ').strip()
            vs.append({'id': vid, 'label': label, 'file': f'p{n}.{vid}.mp3', 'sent': ipa})
        phrases.append({'id': f'p{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ где v звучит как v (не «м», не пропадает)'})
    json.dump({'round': 'es8', 'sections': [{'id': 'v', 'title': 'espeak: v', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
