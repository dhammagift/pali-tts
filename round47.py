"""Round 47, after round 46 (owner, DN 22):
- phoṭṭhabba: p + separate h (b of round 46) "only starting to go the right way"; further along that line:
  voiced ɦ after p, a long p before h, a doubled p before h.
- Dukkhanirodhagāminiyā read «гаминья» (the i before yā lost): doubled jj (as j in round 36), tense i, long iː.
- paṭipadāya: only the doubled ʈʈ had an ok (1 of 2); again against the current one, in a second phrase too.
- tiṭṭhatu / tiṭṭhantu: every spelling of round 46 was ok in at most 1 of 4; ʈː + h again, and ʈː + voiced ɦ.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round47.py -> out/r47/; then build_page.py with ROUND = 'r47'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r47'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('ph', 'phoṭṭhabba: p + h, дальше в ту сторону', '★ где «пхоттхабба», без «ф»',
     ['Rasavitakko loke, phoṭṭhabbavitakko loke.'],
     [('a', 'p + отдельное h (b раунда 46)', word('pʰoʈːʰ', 'phoʈːʰ')),
      ('b', 'p + звонкое ɦ', word('pʰoʈːʰ', 'pɦoʈːʰ')),
      ('c', 'долгое p + h', word('pʰoʈːʰ', 'pːhoʈːʰ')),
      ('d', 'удвоенное p + h', word('pʰoʈːʰ', 'pphoʈːʰ'))]),
    ('gami', 'gāminiyā: «гаминья»', '★ где «гаминия», i перед yā слышно',
     ['Dukkhanirodhagāminiyā paṭipadāya ñāṇaṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'удвоенное jj', lambda s: s.replace('mɪnɪjaː', 'mɪnɪjjaː')),
      ('c', 'напряжённое i', lambda s: s.replace('mɪnɪjaː', 'mɪnijaː')),
      ('d', 'долгое iː', lambda s: s.replace('mɪnɪjaː', 'mɪniːjaː'))]),
    ('pati', 'paṭipadā: «пратипада»', '★ где «патипада», без «р»',
     ['Dukkhanirodhagāminiyā paṭipadāya ñāṇaṁ.', 'Ayaṁ vuccatāvuso, dukkhanirodhagāminī paṭipadā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'удвоенное ʈʈ (ok 1 из 2 в раунде 46)', lambda s: s.replace('pʌʈɪp', 'pʌʈʈɪp').replace('pʌʈˈɪp', 'pʌʈʈˈɪp'))]),
    ('titth', 'tiṭṭhatu, tiṭṭhantu: «чичату»', '★ где «титтхату», без «ч»',
     ['Tiṭṭhatu, bhikkhave, ekaṁ vassaṁ.', 'Tiṭṭhantu, bhikkhave, sattavassāni.'],
     [('a', 'как сейчас (ʈːʰ)', lambda s: s),
      ('b', 'ʈː + отдельное h', word('ʈːʰ', 'ʈːh')),
      ('c', 'ʈː + звонкое ɦ', word('ʈːʰ', 'ʈːɦ'))]),
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
    json.dump({'round': 'r47', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
