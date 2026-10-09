"""Round 52, after round 50 (owner):
- Aññabhāgiya ends «гья» instead of «гийя»: the i before a word-final ya is lost (as gāminiyā «гаминья», round 47,
  where jj, a tense i and a long iː were all ok). The same three here.
- paggayha read «пагейа»: y and h melt into an e. Doubled jj, a long h, a long j.
- dhārayāmīti «дхареямити»: the short a before y turns e. Single j was ok 1 of 2 (jj 0 of 2); the open a with j / jj.
- a lone h: long hː 4 of 6 against h 3 of 6 - too close; again on hoti, bhikkhūhi, mahā.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round52.py -> out/r52/; then build_page.py with ROUND = 'r52'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r52'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('iya', '-iya в конце слова: «гья»', '★ где «-гийя» целиком',
     ['Aññabhāgiyassa adhikaraṇassa.', 'Vijjābhāgiyā dhammā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'напряжённое i', lambda s: s.replace('ɡɪj', 'ɡij')),
      ('c', 'удвоенное jj (как gāminiyā)', lambda s: s.replace('ɡɪj', 'ɡɪjj')),
      ('d', 'долгое iː', lambda s: s.replace('ɡɪj', 'ɡiːj'))]),
    ('yh', 'paggayha: «пагейа»', '★ где «паггайха»',
     ['Samādāya paggayha aṭṭhāsi.'],
     [('a', 'как сейчас (jh)', lambda s: s),
      ('b', 'jj + h', lambda s: s.replace('ʌjhʌ', 'ʌjjhʌ')),
      ('c', 'долгое hː', lambda s: s.replace('ʌjhʌ', 'ʌjhːʌ')),
      ('d', 'долгое jː', lambda s: s.replace('ʌjhʌ', 'ʌjːhʌ'))]),
    ('dhar', 'dhārayāmīti: «дхареямити»', '★ где «дхараямити»',
     ['Tasmā tuṇhī, evametaṁ dhārayāmīti.'],
     [('a', 'как сейчас (ʌjj)', lambda s: s),
      ('b', 'одно j (ok 1 из 2 в раунде 50)', lambda s: s.replace('ɾʌjjaː', 'ɾʌjaː')),
      ('c', 'открытое a + j', lambda s: s.replace('ɾʌjjaː', 'ɾajaː')),
      ('d', 'открытое a + jj', lambda s: s.replace('ɾʌjjaː', 'ɾajjaː'))]),
    ('h', 'отдельное h', '★ где h полноценное',
     ['Ayampi pārājiko hoti asaṁvāso.', 'So bhikkhu bhikkhūhi vuccamāno.', 'Mahā kho, bhikkhave.'],
     [('a', 'как сейчас (h)', lambda s: s),
      ('b', 'долгое hː (4 из 6 в раунде 50)', lambda s: s.replace('h', 'hː').replace('hːʰ', 'hʰ'))]),
    ('puc', 'pucchāmi: «паччхами»', '★ где «пуччхами»',
     ['Tatthāyasmante pucchāmi.'],
     [('a', 'как сейчас (ʊ)', lambda s: s),
      ('b', 'напряжённое u', lambda s: s.replace('pʊccʰ', 'puccʰ')),
      ('c', 'долгое uː', lambda s: s.replace('pʊccʰ', 'puːccʰ'))]),
    ('noise', 'ṭṭh: меньше случайности в голосе', '★ где «ттх», без «ч»',
     ['Sammādiṭṭhi, sammāsaṅkappo.', 'Tiṭṭhantu, bhikkhave, satta vassāni.', 'Uddiṭṭhaṁ kho āyasmanto nidānaṁ.'],
     [('a', 'как сейчас (шум 0.6/0.7)', lambda s: s),
      ('b', 'шум 0.3/0.3', lambda s: s, (0.3, 0.3)),
      ('c', 'шум 0.1/0.1', lambda s: s, (0.1, 0.1))]),
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
            for vid, label, fn, *noise in variants:
                s = fn(base)
                assert vid == 'a' or noise or s != base, (sid, vid, base)
                cfg = SynthesisConfig(length_scale=CFG.length_scale, noise_scale=noise[0][0], noise_w_scale=noise[0][1]) if noise else CFG
                for take in (1, 2):
                    f = f'{sid}{i}.{vid}{take}.mp3'
                    vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
                    if os.path.exists(f'{OUT}/{f}'):  # rendered before: keep the take that was voted on
                        continue
                    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), cfg)
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                    '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title + ', 0.7x', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'r52', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
