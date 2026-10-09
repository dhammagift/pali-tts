"""Round 43: more of DN 22 as heard in the app (r31 rules): byagghehi, caparaṁ, Aṭṭhikasaṅkhalikaṁ, aññena (no
detail given: the current reading plus likely fixes, comments asked), and "So imameva kāyaṁ" - So read apart from the
rest («соо», then the sentence): that is round 17's pause after a one-syllable word before a vowel (MONO_HIATUS).
0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round43.py -> out/r43/; then build_page.py with ROUND = 'r43'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r43'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('so', 'So imameva: «соо» отдельно от фразы', '★ где So звучит вместе с фразой и без «соо»',
     ['So imameva kāyaṁ upasaṁharati.'],
     [('a', 'как сейчас (пауза после So, правило раунда 17)', lambda s: s),
      ('b', 'без паузы', word('sˈoː, ', 'sˈoː ')),
      ('c', 'без паузы, короткое o', word('sˈoː, ', 'sˈo ')),
      ('d', 'без паузы, без ударения на So', word('sˈoː, ', 'soː '))]),
    ('by', 'byagghehi', '★ где «бйаггхехи» чисто',
     ['Sunakhehi vā khajjamānaṁ byagghehi vā khajjamānaṁ.'],
     [('a', 'как сейчас (bj)', lambda s: s),
      ('b', 'b + i + j («бияггхехи»)', word('bjʌɡ', 'bɪjʌɡ')),
      ('c', 'двойное jj', word('bjʌɡ', 'bjjʌɡ')),
      ('d', 'ударение на bya', word('bjʌɡɡʰˈeː', 'bjˈʌɡɡʰeː'))]),
    ('capa', 'caparaṁ', '★ где «чапарам» чисто',
     ['Puna caparaṁ, bhikkhave, bhikkhu gacchanto vā gacchāmīti pajānāti.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое a после p', word('cˈʌpʌɾən', 'cˈʌpaɾən')),
      ('c', 'ударение на pa', word('cˈʌpʌɾən', 'cʌpˈʌɾən')),
      ('d', 'cc в начале (одиночное c бывало «щ»)', word('cˈʌpʌɾən', 'ccˈʌpʌɾən'))]),
    ('sankh', 'Aṭṭhikasaṅkhalikaṁ', '★ где «аттхикасанкхаликам» чисто',
     ['Aṭṭhikasaṅkhalikaṁ nimaṁsalohitamakkhitaṁ nhārusambandhaṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'ударение на kha', word('sˈʌŋkʰʌlɪkən', 'sʌŋkʰˈʌlɪkən')),
      ('c', 'открытое a после kh', word('sˈʌŋkʰʌlɪkən', 'sˈʌŋkʰalɪkən')),
      ('d', 'ударение на li', word('sˈʌŋkʰʌlɪkən', 'sʌŋkʰʌlˈɪkən'))]),
    ('nn', 'aññena', '★ где «аньньена» чисто',
     ['Aññena hatthaṭṭhikaṁ aññena pādaṭṭhikaṁ.'],
     [('a', 'как сейчас (ɲːj)', lambda s: s),
      ('b', 'открытое a в конце', lambda s: s.replace('ɲːjˈeːnʌ', 'ɲːjˈeːna')),
      ('c', 'одно ɲj', lambda s: s.replace('ɲːjˈeːnʌ', 'ɲjˈeːnʌ')),
      ('d', 'nɲ (n + мягкое)', lambda s: s.replace('ɲːjˈeːnʌ', 'nɲjˈeːnʌ'))]),
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
    json.dump({'round': 'r43', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
