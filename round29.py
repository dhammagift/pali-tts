"""Round 29: the owner doesn't believe pratham can't say a final ṁ - so the hard words written in plain Hindi
(Devanagari) and read the way any Hindi text is: espeak-ng hi phonemes -> pratham. Three spellings of ṁ:
anusvara ं, ṅ with virama ङ्, ṅg ङ्ग; and our current Pali phonemes for comparison. Names shown (not blind).
Usage: .venv/bin/python round29.py -> out/r29/; then build_page.py with ROUND = 'r29'
"""
import json
import os

from piper import PiperVoice

from pali_ipa import to_ipa, tune
from round26 import render, synth_cut

OUT = 'out/r29'
WORDS = [('Yāyaṁ taṇhā', 'यायं तण्हा'), ('viññāṇaṁ', 'विञ्ञाणं'), ('Dutiyaṁ', 'दुतियं'), ('Paṭhamaṁ', 'पठमं'),
         ('dukkhaṁ', 'दुक्खं'), ('cakkhuṁ', 'चक्खुं'), ('saddamanussāvesuṁ', 'सद्दमनुस्सावेसुं'), ('imasmiṁ', 'इमस्मिं'),
         ('Evaṁ me sutaṁ.', 'एवं मे सुतं।'), ('Idaṁ dukkhaṁ ariyasaccaṁ.', 'इदं दुक्खं अरियसच्चं।')]
SPELL = [('a', 'хинди: ं (анусвара)', lambda d: d),
         ('b', 'хинди: ङ् (ṅ с вирамой)', lambda d: d.replace('ं', 'ङ्')),
         ('c', 'хинди: ङ्ग (ṅg)', lambda d: d.replace('ं', 'ङ्ग'))]

if __name__ == '__main__':
    pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for n, (iast, deva) in enumerate(WORDS):
        vs = []
        for vid, label, fn in SPELL:
            d = fn(deva)
            ph = ''.join(sum(pratham.phonemize(d), []))
            f = f'w{n}.{vid}.mp3'
            render(synth_cut(list(ph), []), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': f'{label}: {d} → {ph}', 'file': f, 'sent': ph})
        ours = tune(to_ipa(iast, full_a=True))
        render(synth_cut(list(ours), []), f'{OUT}/w{n}.z.mp3')
        vs.append({'id': 'z', 'label': f'наши фонемы пали (как сейчас на сайте): {ours}', 'file': f'w{n}.z.mp3', 'sent': ours})
        phrases.append({'id': f'w{n}', 'text': iast, 'ipa': '', 'script': deva, 'variants': vs,
                        'note': '★ где конечное ṁ звучит правильно (можно несколько)'})
    json.dump({'round': 'r29', 'sections': [{'id': 'w', 'title': 'Конечное ṁ чистым хинди', 'multi_best': True, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for p in phrases:
        print(p['text'], '|', ' | '.join(v['label'].split(': ', 1)[1] for v in p['variants']))
