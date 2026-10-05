"""espeak-ng `pi`: word-final ṁ in espeak's own voice. es2: it sounds like a plain н; the owner: it must be neither
н nor м. Variants fed as espeak phonemes ([[...]]), the rest of the line unchanged. Blind.
Usage: python3 round_es3.py -> out/es3/; then build_page.py with ROUND = 'es3'
"""
import json
import os
import re
import subprocess

ESPEAK = '/root/build/espeak-ng'
ENV = dict(os.environ, ESPEAK_DATA_PATH=f'{ESPEAK}/build')
BIN = f'{ESPEAK}/build/src/espeak-ng'
OUT = 'out/es3'
TEXTS = ['Idaṁ kho pana, bhikkhave, dukkhaṁ ariyasaccaṁ.', 'Ñāṇaṁ udapādi, vijjā udapādi.',
         'Atthi imasmiṁ kāye.', 'Brahmakāyikā devā saddamanussāvesuṁ.', 'Evaṁ me sutaṁ.']
FINAL = re.compile(r'([VaIiUuoe]):?N(?=$|[\s_])')  # a vowel + N at a word end (espeak's ṁ)
VARIANTS = [('a', 'как сейчас: ŋ', lambda m: m.group(0)),
            ('b', 'долгое ŋŋ', lambda m: m.group(0) + 'N'),
            ('c', 'носовая гласная + ŋ', lambda m: m.group(1) + ':~N' if m.group(0)[1:2] == ':' else m.group(1) + '~N'),
            ('d', 'носовая гласная + долгое ŋŋ', lambda m: (m.group(1) + ':~NN') if m.group(0)[1:2] == ':' else m.group(1) + '~NN')]


def phonemes(text):
    return subprocess.run([BIN, '-q', '-x', '-v', 'pi', text], env=ENV, capture_output=True, text=True, check=True).stdout


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for n, text in enumerate(TEXTS):
        clauses = [c.strip() for c in phonemes(text).splitlines() if c.strip()]
        vs = []
        for vid, label, fn in VARIANTS:
            ph = [FINAL.sub(fn, c) for c in clauses]
            assert vid == 'a' or ph != clauses, (text, vid)
            wav = subprocess.run([BIN, '-v', 'pi', '-s', '140', '--stdout', ' '.join(f'[[{c}]],' for c in ph)],
                                 env=ENV, capture_output=True, check=True).stdout
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-ac', '1', '-q:a', '6', f'{OUT}/p{n}.{vid}.mp3'],
                           input=wav, check=True)
            ipa = subprocess.run([BIN, '-q', '--ipa', '-v', 'pi', ' '.join(f'[[{c}]],' for c in ph)], env=ENV,
                                 capture_output=True, text=True, check=True).stdout.replace('\n', ' ').strip()
            vs.append({'id': vid, 'label': f'{label} · {ipa}', 'file': f'p{n}.{vid}.mp3'})
        phrases.append({'id': f'p{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ где конечное ṁ звучит как ṁ — не «н» и не «м»'})
    json.dump({'round': 'es3', 'sections': [{'id': 'm', 'title': 'espeak: конечное ṁ', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps([v['label'] for v in phrases[0]['variants']], ensure_ascii=False))
