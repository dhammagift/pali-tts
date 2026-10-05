"""espeak-ng `pi` on the owner's glossary (Google Sheet, 354 terms): only the terms with the sounds earlier rounds
stumbled on - r, v, j, initial ñ, word-final ṁ, ḷ, doubled aspirates, long compounds. espeak's own voice + pratham
and the own voice reading the same espeak phonemes.
Usage: .venv/bin/python round_es5.py -> out/es5/; then build_page.py with ROUND = 'es5'
"""
import json
import os

from piper import PiperVoice

from round_es1 import neural, speak

OUT = 'out/es5'
GROUPS = [
    ('r', 'r', ['arahaṁ', 'ariyo aṭṭhaṅgiko maggo', 'nirodha', 'rāga', 'saṅkhāra', 'vīriya', 'brahmacariya',
                'parinibbāna', 'anuttaro purisadammasārathi', 'nīvaraṇa']),
    ('v', 'v', ['avijjā', 'vedanā', 'āvuso', 'vicikicchā', 'viññāṇa', 'vūpasama', 'bhavataṇhā', 'vāyodhātu']),
    ('j', 'j', ['jhāna', 'jivhā', 'ujuppaṭipanno', 'pāmojja', 'sampajāna']),
    ('n', 'ñ', ['ñāṇadassana', 'ñāyappaṭipanno', 'ākiñcaññāyatana', 'nevasaññānāsaññāyatana', 'viññāṇañcāyatana']),
    ('m', 'конечное ṁ', ['yathābhūtaṁ', 'paccattaṁ veditabbo viññūhi', 'satthā devamanussānaṁ',
                         'anuttaraṁ puññakkhettaṁ lokassa', 'ehi tvaṁ', 'evamevaṁ', 'yampicchaṁ na labhati']),
    ('d', 'ḷ, придыхательные, двойные', ['saḷāyatana', 'dakkhiṇeyyo', 'phoṭṭhabba', 'uddhaccakukkucca', 'thinamiddha',
                                         'samphappalāpa', 'abhijjhā', 'paññindriya', 'svākkhāto', 'ehipassiko']),
    ('c', 'длинные слова', ['chandasamādhippadhānasaṅkhārasamannāgata iddhipāda', 'saññāvedayitanirodha',
                            'sīlabbataparāmāsa', 'kāmesumicchācāra', 'tatratatrābhinandinī', 'sakkāyadiṭṭhi', 'opaneyyiko']),
]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    voices = [('pr', 'pratham по фонемам espeak', PiperVoice.load('models/hi_IN-pratham-medium.onnx'), 1.15),
              ('dg', 'свой голос по фонемам espeak', PiperVoice.load('models/pali_dg-medium.onnx'), 1.0)]
    sections = []
    for sid, title, words in GROUPS:
        phrases = []
        for n, text in enumerate(words):
            pid = f'{sid}{n}'
            ipa = speak(text, f'{OUT}/{pid}.mp3')
            vs = [{'id': 'es', 'label': 'espeak-ng pi', 'file': f'{pid}.mp3'}]
            for vid, label, voice, length in voices:
                neural(voice, ipa, length, f'{OUT}/{pid}.{vid}.mp3')
                vs.append({'id': vid, 'label': label, 'file': f'{pid}.{vid}.mp3'})
            phrases.append({'id': pid, 'text': text, 'ipa': ipa, 'script': '', 'variants': vs,
                            'note': '✓ правильно / ✗ ошибка; нажми на неправильное слово'})
        sections.append({'id': sid, 'title': f'Глоссарий: {title}', 'multi_best': True, 'phrases': phrases})
    json.dump({'round': 'es5', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(sum(len(s['phrases']) for s in sections), 'terms')
