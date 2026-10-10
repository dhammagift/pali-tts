"""Round 54, leftovers of rounds 52-53 (owner):
- paggayha «пагейа»: every spelling of round 52 bad. The short a before y melts into e (Hindi ay), as in dhārayāmīti,
  where an open a fixed it (round 52) - so the open a here.
- asaṁvāso, marked by the owner (round 52): an open a before the ṁ, a doubled ŋŋ, a nasal vowel + ŋ.
- bhikkhusammutiyā: jj won (round 53), but «not a proper u»: a long uː, as pucchāmi (round 52).
- tikkhattuṁ: the i lost, the ṁ never read (round 53): a long iː, and with the stress on it.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round54.py -> out/r54/; then build_page.py with ROUND = 'r54'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r54'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('yh', 'paggayha: «пагейа»', '★ где «паггайха»',
     ['Samādāya paggayha aṭṭhāsi.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое a перед y (как dhārayāmīti)', lambda s: s.replace('ˈʌjhʌ', 'ˈajhʌ')),
      ('c', 'открытое a + jj', lambda s: s.replace('ˈʌjhʌ', 'ˈajjhʌ')),
      ('d', 'открытое a + долгое h', lambda s: s.replace('ˈʌjhʌ', 'ˈajhːʌ'))]),
    ('asam', 'asaṁvāso', '★ где «асамваасо» правильно',
     ['Ayampi pārājiko hoti asaṁvāso.'],
     [('a', 'как сейчас (ŋʋ)', lambda s: s),
      ('b', 'открытое a перед ṁ', lambda s: s.replace('ʌsʌŋʋ', 'ʌsaŋʋ')),
      ('c', 'удвоенное ŋŋ', lambda s: s.replace('ʌsʌŋʋ', 'ʌsʌŋŋʋ')),
      ('d', 'носовая гласная + ŋ', lambda s: s.replace('ʌsʌŋʋ', 'ʌsʌ\u0303ŋʋ'))]),
    ('sam', 'bhikkhusammutiyā: u', '★ где «саммутийа» с нормальным u',
     ['Aññatra bhikkhusammutiyā.'],
     [('a', 'как сейчас (jj, лучшее в раунде 53)', lambda s: s),
      ('b', 'долгое uː (как pucchāmi)', lambda s: s.replace('mmʊtɪjj', 'mmuːtɪjj'))]),
    ('tikkh', 'tikkhattuṁ: без i и без ṁ', '★ где «тиккхаттум» целиком',
     ['Tikkhattuṁ padakkhiṇaṁ katvā.', 'Dvattikkhattuṁ codetabbo.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'долгое iː', lambda s: s.replace('tɪkkʰˈʌttu', 'tiːkkʰˈʌttu')),
      ('c', 'долгое iː под ударением', lambda s: s.replace('tɪkkʰˈʌttu', 'tˈiːkkʰʌttu'))]),
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
    json.dump({'round': 'r54', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
