"""espeak-ng `pi`, es5 notes: doubled consonants too strong ("памоджжа" should be "паамодджа"), h too strong
(brahmacariya, jivhā). Variants fed as espeak phonemes ([[...]]); h candidates are temporary phonemes h1/h2. Blind.
Usage: python3 round_es6.py -> out/es6/; then build_page.py with ROUND = 'es6'
"""
import json
import os
import re
import subprocess

from round_es3 import BIN, ENV, phonemes

OUT = 'out/es6'
STOP2 = re.compile(r'([kgtdpb]|t\.|d\.)\1')  # a doubled stop (aspiration '#' follows the second one)
SECTIONS = [
    ('a', 'двойные ч / дж (jj, cc, cch)', '★ где двойное звучит как «дж» / «тч» с задержкой, а не «дж-дж»',
     ['avijjā', 'pāmojja', 'vicikicchā', 'kāmesumicchācāra', 'yampicchaṁ na labhati', 'uddhaccakukkucca'],
     [('a', 'сейчас: два звука подряд', lambda s: s),
      ('b', 'д+дж, т+ч (смычка, потом один звук)', lambda s: s.replace('JJ', 'dJ').replace('cc', 'tc'))]),
    ('b', 'другие двойные (kk, pp, ṭṭh, ddh)', '★ где двойное звучит естественно: с задержкой, но не отрывисто',
     ['samphappalāpa', 'appamāda', 'dakkhiṇeyyo', 'phoṭṭhabba', 'sakkāyadiṭṭhi', 'buddho'],
     [('a', 'сейчас: два взрыва', lambda s: s),
      ('b', 'пауза-смычка + один звук', lambda s: STOP2.sub(r'_\1', s)),
      ('c', 'один звук (без удвоения)', lambda s: STOP2.sub(r'\1', s))]),
    ('h', 'h', '★ где h звучит лёгким выдохом, не слишком сильно',
     ['brahmacariya', 'jivhā', 'ehi tvaṁ', 'vihāra', 'mahābhūta'],
     [('a', 'сейчас (хинди h)', lambda s: s),
      ('b', 'тихая h (латышская)', lambda s: s.replace('H', 'h1')),
      ('c', 'бирманская h', lambda s: s.replace('H', 'h2'))]),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, note, texts, variants in SECTIONS:
        phrases = []
        for n, text in enumerate(texts):
            clauses = [c.strip() for c in phonemes(text).splitlines() if c.strip()]
            vs = []
            for vid, label, fn in variants:
                ph = [fn(c) for c in clauses]
                assert vid == 'a' or ph != clauses, (sid, text, vid, clauses)
                wav = subprocess.run([BIN, '-v', 'pi', '-s', '140', '--stdout', ' '.join(f'[[{c}]],' for c in ph)],
                                     env=ENV, capture_output=True, check=True).stdout
                f = f'{sid}{n}.{vid}.mp3'
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-ac', '1', '-q:a', '6', f'{OUT}/{f}'], input=wav, check=True)
                vs.append({'id': vid, 'label': label, 'file': f})
            phrases.append({'id': f'{sid}{n}', 'text': text, 'ipa': '', 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': f'espeak: {title}', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'es6', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
