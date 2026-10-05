"""espeak-ng `pi`: r and v in espeak's own voice. es2: the tap r is still "not a normal r", and v vanished in
saddamanussāvesuṁ. Candidates come from other espeak tables (temporary phonemes r2..r4, v1..v3 in ph_pali). Blind.
Usage: python3 round_es4.py -> out/es4/; then build_page.py with ROUND = 'es4'
"""
import json
import os
import subprocess

from round_es3 import BIN, ENV, phonemes

OUT = 'out/es4'
SECTIONS = [
    ('r', 'r', '★ где r звучит как нормальная r пали', '*',
     ['Ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati.', 'passambhayaṁ kāyasaṅkhāraṁ', 'Tatra kho bhagavā pañcavaggiye bhikkhū āmantesi.',
      'Idaṁ kho pana, bhikkhave, dukkhanirodhaṁ ariyasaccaṁ.', 'paranimmitavasavattī devā, brahmakāyikā devā.'],
     [('a', 'сейчас: удар (Hindi flap)', '*'), ('b', 'русская r', 'r2'), ('c', 'испанская r', 'r3'), ('d', 'хинди r (как в es1)', 'r4')]),
    ('v', 'v', '★ где v звучит чётко и правильно, не «м» и не пропадает', 'v',
     ['Brahmakāyikā devā saddamanussāvesuṁ.', 'samaṇena vā brāhmaṇena vā devena vā mārena vā brahmunā vā.',
      'Ekaṁ samayaṁ bhagavā viharati.'],
     [('a', 'сейчас (base v)', 'v'), ('b', 'хинди ʋ (как в es1)', 'v1'), ('c', 'русская в', 'v2'), ('d', 'итальянская v', 'v3')]),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, note, sym, texts, variants in SECTIONS:
        phrases = []
        for n, text in enumerate(texts):
            clauses = [c.strip() for c in phonemes(text).splitlines() if c.strip()]
            assert any(sym in c for c in clauses), (text, clauses)
            vs = []
            for vid, label, rep in variants:
                ph = ' '.join(f'[[{c.replace(sym, rep)}]],' for c in clauses)
                wav = subprocess.run([BIN, '-v', 'pi', '-s', '140', '--stdout', ph], env=ENV, capture_output=True, check=True).stdout
                f = f'{sid}{n}.{vid}.mp3'
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-ac', '1', '-q:a', '6', f'{OUT}/{f}'], input=wav, check=True)
                vs.append({'id': vid, 'label': label, 'file': f})
            phrases.append({'id': f'{sid}{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': f'espeak: {title}', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'es4', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
