"""Round 51, the rest of the owner's Pātimokkha list (no details, so the variants are guesses), and ṭṭh before i again:
round 49 had the retroflex closure + dental aspirated release (ʈtʰ) best + ok in Niṭṭhite / Sukkavissaṭṭhi, but round 20
kept ʈːʰ for sammādiṭṭhi - so both again on sammādiṭṭhi and Niṭṭhite before any rule.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round51.py -> out/r51/; then build_page.py with ROUND = 'r51'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r51'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('tthi', 'ṭṭh перед i: «ч»', '★ где «ттх», без «ч»',
     ['Sammādiṭṭhi, sammāsaṅkappo.', 'Niṭṭhite navakamme ca.'],
     [('a', 'как сейчас (ʈːʰ)', lambda s: s),
      ('b', 'ʈtʰ (лучшее в раунде 49)', lambda s: s.replace('ʈːʰ', 'ʈtʰ'))]),
    ('nth', 'Taṇṭhāna: ṇṭh', '★ где «таньтхана» правильно',
     ['Taṇṭhānasammajjanañca.'],
     [('a', 'как сейчас (ɳʈʰ)', lambda s: s),
      ('b', 'ɳʈtʰ', lambda s: s.replace('ɳʈʰ', 'ɳʈtʰ')),
      ('c', 'ɳʈ + отдельное h', lambda s: s.replace('ɳʈʰ', 'ɳʈh'))]),
    ('hem', 'hemantagimhavassānānaṁ', '★ где слово целиком и правильно',
     ['Hemantagimhavassānānaṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'побочные ударения на частях слова', lambda s: s.replace('heːmʌntʌɡɪmhʌʋʌss', 'hˌeːmʌntʌɡˌɪmhʌʋˌʌss')),
      ('c', 'h как «х» (x)', lambda s: s.replace('h', 'x'))]),
    ('tes', 'Tesañca: ñc', '★ где «тесаньча»',
     ['Tesañca bhikkhūnaṁ.'],
     [('a', 'как сейчас (nc)', lambda s: s),
      ('b', 'ɲc', lambda s: s.replace('ˈʌncʌ', 'ˈʌɲcʌ'))]),
    ('katum', 'kātuṁ: конечное ṁ', '★ где «катум» с ṁ',
     ['Icchāmahaṁ, ayye, vihāraṁ kātuṁ.'],
     [('a', 'как сейчас (ũ)', lambda s: s),
      ('b', 'ʊm', lambda s: s.replace('kˈaːtu\u0303', 'kˈaːtʊm')),
      ('c', 'ũm', lambda s: s.replace('kˈaːtu\u0303', 'kˈaːtu\u0303m'))]),
    ('upo', 'uposathassa etāni', '★ где оба слова целиком',
     ['Uposathassa etāni, pubbakiccanti vuccati.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'пауза между словами', lambda s: s.replace('ˈʌssʌ eː', 'ˈʌssʌ, eː')),
      ('c', 'открытое a в конце uposathassa', lambda s: s.replace('ˈʌssʌ eː', 'ˈʌssa eː'))]),
    ('tun', 'tuṇhībhāvena: ṇh', '★ где «тунхи» правильно',
     ['Tuṇhībhāvena kho panāyasmante.'],
     [('a', 'как сейчас (ɳh)', lambda s: s),
      ('b', 'ɳ + «х» (x)', lambda s: s.replace('ɳh', 'ɳx')),
      ('c', 'ɳ + звонкое ɦ', lambda s: s.replace('ɳh', 'ɳɦ'))]),
    ('puc', 'pucchāmi: cch', '★ где «пуччхами» правильно',
     ['Tatthāyasmante pucchāmi.'],
     [('a', 'как сейчас (ccʰ)', lambda s: s),
      ('b', 'долгое cːʰ', lambda s: s.replace('ccʰ', 'cːʰ')),
      ('c', 'c + отдельное h', lambda s: s.replace('ccʰ', 'cch'))]),
    ('asam', 'asaṁvāso: ṁv', '★ где «асамвасо» с ṁ',
     ['Ayampi pārājiko hoti asaṁvāso.'],
     [('a', 'как сейчас (ŋʋ)', lambda s: s),
      ('b', 'mʋ', lambda s: s.replace('ŋʋ', 'mʋ')),
      ('c', 'носовая гласная ʌ̃ʋ', lambda s: s.replace('ʌŋʋ', 'ʌ\u0303ʋ'))]),
    ('mama', 'mama', '★ где «мама» целиком',
     ['Viramathāyasmanto mama vacanāya.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое a в конце', lambda s: s.replace('mˈʌmʌ ', 'mˈʌma ')),
      ('c', 'долгое aː в конце', lambda s: s.replace('mˈʌmʌ ', 'mˈʌmaː '))]),
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
    json.dump({'round': 'r51', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
