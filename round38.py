"""Round 38: what round 37 found wrong in BOTH engines (so it is ours, not sherpa's), one question per section:
the word-final o is not held (sampajāno, sugato), tiṇṇaṁ, Tasmātiha, and cakkhu- at the start of a phrase
(cakkhusamphassajā). None of these were judged before for pratham (es1 w19 was the espeak voice). 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round38.py -> out/r38/; then build_page.py with ROUND = 'r38'
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r38'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
END_O = re.compile(r'(?<=[^ ,])oː(?=[ ,.?!:;]|$)')  # a word-final long o


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('o', 'Конечное -o: тянется ли (sampajāno, sugato…)', '★ где конечное о долгое, как надо',
     ['Ātāpī sampajāno satimā.', 'Sammāsambuddho vijjācaraṇasampanno sugato lokavidū.'],
     [('a', 'как сейчас (oː)', lambda s: s),
      ('b', 'oːː (длиннее)', lambda s: END_O.sub('oːː', s)),
      ('c', 'oː с побочным ударением', lambda s: END_O.sub('ˌoː', s))]),
    ('t', 'Tiṇṇaṁ', '★ где tiṇṇaṁ правильно',
     ['Tiṇṇaṁ saṅgati phasso.'],
     [('a', 'как сейчас (ɳɳən)', lambda s: s),
      ('b', 'полное a в конце (ɳɳʌn)', word('tˈɪɳɳən', 'tˈɪɳɳʌn')),
      ('c', 'зубное nn', word('tˈɪɳɳən', 'tˈɪnnən')),
      ('d', 'долгое ɳ', word('tˈɪɳɳən', 'tˈɪɳːən'))]),
    ('s', 'Tasmātiha', '★ где tasmātiha правильно; напиши, что не так в остальных',
     ['Tasmātiha, bhikkhave, yogo karaṇīyo.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое a в конце', word('tʌsmˈaːtɪhʌ', 'tʌsmˈaːtɪha')),
      ('c', 'ss', word('tʌsmˈaːtɪhʌ', 'tʌssmˈaːtɪhʌ')),
      ('d', 'ударение на первый слог', word('tʌsmˈaːtɪhʌ', 'tˈʌsmaːtɪhʌ'))]),
    ('c', 'cakkhu- в начале фразы', '★ где cakkhu- в начале правильно',
     ['Cakkhusamphassajā vedanā, sotasamphassajā vedanā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'побочное ударение на cak-', word('cʌkkʰʊsʌmph', 'cˌʌkkʰʊsʌmph')),
      ('c', 'tʃ вместо c', word('cʌkkʰʊsʌmph', 'tʃʌkkʰʊsʌmph')),
      ('d', 'главное ударение на cak-', word('cʌkkʰʊsʌmphˈʌssʌɟɟaː', 'cˈʌkkʰʊsʌmphʌssʌɟɟaː'))]),
]

if __name__ == '__main__':
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, note, texts, variants in SECTIONS:
        phrases = []
        for i, text in enumerate(texts):
            base = tune(to_ipa(text, full_a=True))
            vs = []
            for vid, label, fn in variants:
                s = fn(base)
                assert vid == 'a' or s != base, (sid, vid, base)
                for take in (1, 2):
                    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
                    f = f'{sid}{i}.{vid}{take}.mp3'
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                    '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
                    vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title + ', 0.7x', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'r38', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
