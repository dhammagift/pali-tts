"""Round 53, the owner's list #3 (Pātimokkha, nissaggiya):
- -aṁ heard as «ан» (dhāretabbaṁ, nissaggiyaṁ pācittiyaṁ, vikappaṁ, maṁ, evarūpaṁ). Round 50: the short nasal
  vowels (ã, ə̃) were bad, ən won; vadeyyuṁ's ũ is right. New: long nasal vowels (ə̃ː, ãː) and a single ŋ.
- bhikkhusammutiyā «самматья»: the u heard as a (as pucchāmi), the i before yā lost (as gāminiyā, Aññabhāgiya).
- aññatra «почти дж»: the j after ɲː (aññena, round 43, was fixed with ɲj).
- kathine «тине»: the first syllable lost.
- dvattikkhattuṁ / tikkhattuṁ «катту», the i lost.
- -uṁ (kātuṁ): ũ is right in one take and anything in the next (owner: it surely can say a fine -uṁ) - the voice's
  noise, as with ṭṭh in round 52: the same ũ with less noise.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round53.py -> out/r53/; then build_page.py with ROUND = 'r53'
"""
import json
import re
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r53'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    rT = '\u0303'
T = '\u0303'  # combining tilde: a nasal vowel
END = r'(?=[ ,.?!:;]|$)'
SECTIONS = [
    ('m', '-aṁ: «ан»', '★ где конечное ṁ, не «н»',
     ['Dasāhaparamaṁ atirekacīvaraṁ dhāretabbaṁ.', 'Nissaggiyaṁ pācittiyaṁ.', 'Evarūpaṁ vikappaṁ āpajjeyya.'],
     [('a', 'как сейчас (ən)', lambda s: s),
      ('b', 'долгое носовое ə̃ː', lambda s: re.sub('[əʌ]n' + END, 'ə' + T + 'ː', s)),
      ('c', 'долгое носовое ãː', lambda s: re.sub('[əʌ]n' + END, 'a' + T + 'ː', s)),
      ('d', 'одно ŋ', lambda s: re.sub('[əʌ]n' + END, 'əŋ', s))]),
    ('iya', 'bhikkhusammutiyā: «самматья»', '★ где «саммутийа»',
     ['Aññatra bhikkhusammutiyā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'напряжённые u и i', lambda s: s.replace('mmʊtɪjaː', 'mmutijaː')),
      ('c', 'jj', lambda s: s.replace('mmʊtɪjaː', 'mmʊtɪjjaː')),
      ('d', 'напряжённое u + jj', lambda s: s.replace('mmʊtɪjaː', 'mmutɪjjaː'))]),
    ('nn', 'aññatra: «дж»', '★ где «аньньятра»',
     ['Aññatra bhikkhusammutiyā.'],
     [('a', 'как сейчас (ɲːj)', lambda s: s),
      ('b', 'ɲj (как aññena)', lambda s: s.replace('ʌɲːjˈʌtɾʌ', 'ʌɲjˈʌtɾʌ')),
      ('c', 'ɲː без j', lambda s: s.replace('ʌɲːjˈʌtɾʌ', 'ʌɲːˈʌtɾʌ'))]),
    ('kath', 'kathine: «тине»', '★ где «катхине» целиком',
     ['Ubbhatasmiṁ kathine.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'ударение на thi', lambda s: s.replace('kˈʌtʰɪneː', 'kʌtʰˈɪneː')),
      ('c', 'удвоенное tth', lambda s: s.replace('kˈʌtʰɪneː', 'kˈʌttʰɪneː')),
      ('d', 't + отдельное h', lambda s: s.replace('kˈʌtʰɪneː', 'kˈʌthɪneː'))]),
    ('tikkh', 'dvattikkhattuṁ: «катту», без i', '★ где «двáттиккхаттум»',
     ['Dvattikkhattuṁ codetabbo.', 'Tikkhattuṁ padakkhiṇaṁ katvā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'напряжённое i', lambda s: s.replace('tɪkkʰ', 'tikkʰ')),
      ('c', 'ударение на ti', lambda s: s.replace('tɪkkʰˈʌttu', 'tˈɪkkʰʌttu').replace('dʋʌttɪkkʰˈʌttu', 'dʋʌttˈɪkkʰʌttu'))]),
    ('um', '-uṁ: то хорошо, то как попало', '★ где конечное -uṁ правильное',
     ['Icchāmahaṁ, ayye, vihāraṁ kātuṁ.', 'Dvattikkhattuṁ codetabbo.', 'Evaṁ vadeyyuṁ.'],
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
    json.dump({'round': 'r53', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
