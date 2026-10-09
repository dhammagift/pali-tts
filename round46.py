"""Round 46: jarā at the end of a phrase read «джа» (DN 22: "Katamā ca, bhikkhave, jarā?"). Rounds 20-23 and 34 were
about jarāpi inside a phrase (a syllable lost, partly at random: round 23); this is the phrase-final rā cut off.
Round 20's best (stress on rā, ɟʌɾˈaː) again here, plus a doubled r and a longer final ā. 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round46.py -> out/r46/; then build_page.py with ROUND = 'r46'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r46'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('jara', 'jarā в конце фразы: «джа»', '★ где слышно «джарā» целиком',
     ['Katamā ca, bhikkhave, jarā?', 'Ayaṁ vuccati, bhikkhave, jarā.'],
     [('a', 'как сейчас (ɟˈʌɾaː)', lambda s: s),
      ('b', 'ударение на rā (лучшее в раунде 20)', word('ɟˈʌɾaː', 'ɟʌɾˈaː')),
      ('c', 'удвоенное r', word('ɟˈʌɾaː', 'ɟˈʌɾɾaː')),
      ('d', 'долгое конечное ā (двойное)', word('ɟˈʌɾaː', 'ɟˈʌɾaːaː'))]),
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
    json.dump({'round': 'r46', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
