"""Round 46: jarā at the end of a phrase read «джа» (DN 22: "Katamā ca, bhikkhave, jarā?"). Rounds 20-23 and 34 were
about jarāpi inside a phrase (a syllable lost, partly at random: round 23); this is the phrase-final rā cut off.
Round 20's best (stress on rā, ɟʌɾˈaː) again here, plus a doubled r and a longer final ā. 0.7x, 2 takes, blind.
Then added (owner, same DN 22): phoṭṭhabba «фоттабба» (ph as f), kattha cut at the end, paṭipadāya once
«пратипада» (ʈ between vowels as Hindi's flap ड़), tiṭṭhatu / tiṭṭhantu «чичату». Files already rendered are kept
(votes stay on the takes they were given).
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
    ('ph', 'phoṭṭhabba: «фоттабба»', '★ где «пхоттхабба», без «ф»',
     ['Rasavitakko loke, phoṭṭhabbavitakko loke.'],
     [('a', 'как сейчас (pʰ)', lambda s: s),
      ('b', 'p + отдельное h (как в samphassa, раунд 33)', word('pʰoʈːʰ', 'phoʈːʰ')),
      ('c', 'p + h, и в ṭṭh тоже отдельное h', word('pʰoʈːʰ', 'phoʈːh'))]),
    ('kattha', 'kattha: обрывается в конце', '★ где «каттха» целиком',
     ['Taṇhā kattha uppajjamānā uppajjati, kattha nivisamānā nivisati?',
      'Taṇhā kattha pahīyamānā pahīyati, kattha nirujjhamānā nirujjhati?'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое a в конце (как pana, раунд 42)', lambda s: s.replace('kˈʌttʰʌ ', 'kˈʌttʰa ')),
      ('c', 'долгое aː в конце', lambda s: s.replace('kˈʌttʰʌ ', 'kˈʌttʰaː ')),
      ('d', 'долгое ʌː в конце', lambda s: s.replace('kˈʌttʰʌ ', 'kˈʌttʰʌː '))]),
    ('pati', 'paṭipadāya: «пратипада»', '★ где «патипадая», без «р»',
     ['Dukkhanirodhagāminiyā paṭipadāya ñāṇaṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'удвоенное ʈʈ (не даёт «р»)', word('pʌʈɪp', 'pʌʈʈɪp')),
      ('c', 'напряжённое i после ṭ', word('pʌʈɪp', 'pʌʈip'))]),
    ('titth', 'tiṭṭhatu, tiṭṭhantu: «чичату»', '★ где «титтхату», без «ч»',
     ['Tiṭṭhatu, bhikkhave, ekaṁ vassaṁ.', 'Tiṭṭhantu, bhikkhave, sattavassāni.'],
     [('a', 'как сейчас (ʈːʰ)', lambda s: s),
      ('b', 'ʈː + отдельное h (ok/ok в раунде 42)', word('ʈːʰ', 'ʈːh')),
      ('c', 'напряжённое i в ti', lambda s: s.replace('tˈɪʈːʰ', 'tˈiʈːʰ').replace('tɪʈːʰ', 'tiʈːʰ')),
      ('d', 'без придыхания ʈː', word('ʈːʰ', 'ʈː'))]),
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
                    f = f'{sid}{i}.{vid}{take}.mp3'
                    vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
                    if os.path.exists(f'{OUT}/{f}'):  # rendered before: keep the take that was voted on
                        continue
                    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), CFG)
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                    '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title + ', 0.7x', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'r46', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
