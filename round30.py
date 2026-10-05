"""Round 30: round 29 showed the Hindi anusvara is what sounds right for a word-final ṁ (6 best of 10):
espeak hi reads ं as ən after a (दुक्खं dˈʊkkʰən) and as a nasal vowel after u (चक्खुं cˈʌkkʰũ), with a secondary
stress on that last syllable in longer words (दुतियं dˈʊtɪjˌən). Here only that ending is taken into our own Pali
phonemes (Hindi's schwa deletion spoiled the rest of the words), with and without the secondary stress.
Usage: .venv/bin/python round30.py -> out/r30/; then build_page.py with ROUND = 'r30'
"""
import json
import os
import re

from piper import PiperVoice

from pali_ipa import to_ipa, tune
from round26 import render, synth_cut

OUT = 'out/r30'
END = r'(?=[ ,.?!:;]|$)'
A = re.compile(r'([ʌa])ŋɡ' + END)  # the current rule makes -aṁ ŋɡ
U = re.compile('ʊŋŋ' + END)
VOWEL = re.compile('[ʌaeoiuɪʊ]')
WORDS = [('Yāyaṁ taṇhā ponobbhavikā.', 'यायं'), ('viññāṇaṁ', 'विञ्ञाणं'), ('Dutiyaṁ', 'दुतियं'), ('Paṭhamaṁ', 'पठमं'),
         ('dukkhaṁ', 'दुक्खं'), ('cakkhuṁ', 'चक्खुं'), ('Brahmakāyikā devā saddamanussāvesuṁ.', 'सद्दमनुस्सावेसुं'),
         ('Evaṁ me sutaṁ.', 'एवं मे सुतं।'), ('Idaṁ dukkhaṁ ariyasaccaṁ.', 'इदं दुक्खं अरियसच्चं।'),
         ('Cakkhuṁ udapādi, ñāṇaṁ udapādi, paññā udapādi.', ''), ('Anuttaraṁ sammāsambodhiṁ abhisambuddho.', ''),
         ('satthā devamanussānaṁ', ''), ('yathābhūtaṁ ñāṇadassanaṁ', '')]


def anusvara(s, secondary):
    def a(m):
        word = s[:m.start()].split(' ')[-1]
        return ('ˌ' if secondary and len(VOWEL.findall(word)) >= 2 and 'ˈ' in word else '') + 'ən'
    return U.sub('u\u0303', A.sub(a, s))  # u + combining tilde: pratham's map has no precomposed ũ


if __name__ == '__main__':
    pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for n, (text, deva) in enumerate(WORDS):
        base = tune(to_ipa(text, full_a=True))
        vs = []
        for vid, label, s in [('b', 'наше слово + окончание хинди (ən / ũ)', anusvara(base, False)),
                              ('c', 'то же + второстепенное ударение на конце', anusvara(base, True))]:
            if vid == 'c' and s == vs[-1]['sent']:
                continue  # short words: the same as b
            render(synth_cut(list(s), []), f'{OUT}/w{n}.{vid}.mp3')
            vs.append({'id': vid, 'label': f'{label}: {s}', 'file': f'w{n}.{vid}.mp3', 'sent': s})
        if deva:
            ph = ''.join(sum(pratham.phonemize(deva), []))
            render(synth_cut(list(ph), []), f'{OUT}/w{n}.a.mp3')
            vs.insert(0, {'id': 'a', 'label': f'хинди ं (победитель r29): {deva} → {ph}', 'file': f'w{n}.a.mp3', 'sent': ph})
        assert vs[-1]['sent'] != base, (text, base)  # the rule must change something
        phrases.append({'id': f'w{n}', 'text': text, 'ipa': base, 'script': deva, 'variants': vs,
                        'note': '★ где конечное ṁ звучит правильно (можно несколько)'})
        print(text, '|', ' | '.join(v['sent'] for v in vs))
    json.dump({'round': 'r30', 'sections': [{'id': 'w', 'title': 'Конечное ṁ: окончание хинди в наших словах', 'multi_best': True, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
