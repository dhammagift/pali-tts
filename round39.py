"""Round 39: round 38 again for the two that no variant fixed. The word-final o sounded ordinary (short) in all of
oː / oːː / ˌoː; the final ha of Tasmātiha was not heard in any of hʌ / ha / ss / initial stress. tiṇṇaṁ (ɳː won)
and cakkhu- (as it is, all fine) are settled. Stronger means this time. 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round39.py -> out/r39/; then build_page.py with ROUND = 'r39'
"""
import json
import os
import re
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r39'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
END_O = re.compile(r'(?<=[^ ,])oː(?=[ ,.?!:;]|$)')  # a word-final long o


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('o', 'Конечное -o, ещё раз: тянется ли (sampajāno, sugato…)', '★ где конечное о долгое, как надо',
     ['Ātāpī sampajāno satimā.', 'Sammāsambuddho vijjācaraṇasampanno sugato lokavidū.'],
     [('a', 'как сейчас (oː)', lambda s: s),
      ('b', 'два o подряд (oːoː)', lambda s: END_O.sub('oːoː', s)),
      ('c', 'открытое долгое ɔːː', lambda s: END_O.sub('ɔːː', s)),
      ('d', 'главное ударение на конечное o', lambda s: END_O.sub('ˈoː', s)),
      ('e', 'oː + полудолгота (oːˑ)', lambda s: END_O.sub('oːˑ', s))]),
    ('s', 'Tasmātiha, ещё раз: слышно ли -ha', '★ где -ha в конце слышно',
     ['Tasmātiha, bhikkhave, yogo karaṇīyo.'],
     [('a', 'как сейчас (hʌ)', lambda s: s),
      ('b', 'звонкое ɦ, как хинди ह', word('tʌsmˈaːtɪhʌ', 'tʌsmˈaːtɪɦʌ')),
      ('c', 'долгое a (haː)', word('tʌsmˈaːtɪhʌ', 'tʌsmˈaːtɪhaː')),
      ('d', 'звонкое и долгое (ɦaː)', word('tʌsmˈaːtɪhʌ', 'tʌsmˈaːtɪɦaː')),
      ('e', 'двойное h (hhʌ)', word('tʌsmˈaːtɪhʌ', 'tʌsmˈaːtɪhhʌ'))]),
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
    json.dump({'round': 'r39', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
