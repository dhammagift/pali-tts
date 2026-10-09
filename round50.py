"""Round 50 (owner, Pātimokkha in the app; no details yet, so the variants are guesses):
- iso: a word read on its own (the rule titles Sañcaritta, Aññabhāgiya, Sukkavissaṭṭhi) is misread much worse than
  inside a sentence. As now; with a full stop; slower; read inside "W, W." and the second W cut out with the
  model's own durations (the align onnx of round 26).
- h: a lone h comes out too soft, "like aspiration" - it must be a full h. As now (h); Russian х (x); long hː;
  Hindi voiced ɦ.
- m: word-final -aṁ is heard as a plain n, while vadeyyuṁ's ũ (u + nasal tilde) is right. Round 24 tried a nasal
  ʌ̃ (bad); here the open vowels with the tilde, as ũ is: ã, ə̃, and ə̃n.
- y: dhārayāmīti - the y doubled to jj (rounds 25, 27) against a single j.
0.7x, 2 takes, blind. Usage (on f3): .venv/bin/python round50.py -> out/r50/; then build_page.py with ROUND = 'r50'
"""
import json
import os
import re
import subprocess

import numpy as np
import onnxruntime as ort
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r50'
LENGTH = 1.15 / 0.7
CFG = SynthesisConfig(length_scale=LENGTH, noise_scale=0.6, noise_w_scale=0.7)
END = r'(?=[ ,.?!:;]|$)'
TILDE = '̃'


def carrier_cut(ipa):
    """Read 'W, W.' and keep the second W: the model's durations say where it starts."""
    chars = list(f'{ipa}, {ipa}.')
    ids = IDS['^'] + IDS['_']
    for c in chars:
        ids += IDS[c] + IDS['_']
    ids += IDS['$']
    audio, dur = SESSION.run(None, {'input': np.array([ids], dtype=np.int64),
                                    'input_lengths': np.array([len(ids)], dtype=np.int64),
                                    'scales': np.array([0.6, LENGTH, 0.7], dtype=np.float32)})
    audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
    starts = np.concatenate([[0], np.cumsum(dur)])
    j = len(ipa) + 2  # the second W's first phoneme (after ", ")
    a = starts[2 + 2 * j] - int(0.03 * SR)
    return np.concatenate([np.zeros(int(0.15 * SR), np.float32), audio[max(a, 0):]])


SECTIONS = [
    ('iso', 'слово отдельно (заголовок правила)', '★ где слово прочитано правильно',
     ['Sañcaritta', 'Aññabhāgiya', 'Sukkavissaṭṭhi'],
     [('a', 'как сейчас (одно слово)', lambda s: s),
      ('b', 'с точкой в конце', lambda s: s + '.'),
      ('c', 'медленнее', ('slow', 1.3)),
      ('d', 'внутри «W, W.», второе вырезано', ('carrier',))]),
    ('h', 'отдельное h: слишком мягкое', '★ где h полноценное',
     ['Haneyyuṁ vā bandheyyuṁ vā pabbājeyyuṁ vā.', 'Samādāya paggayha aṭṭhāsi.', 'Tuṇhībhāvena kho panāyasmante.'],
     [('a', 'как сейчас (h)', lambda s: s),
      ('b', 'русское «х» (x)', lambda s: s.replace('h', 'x')),
      ('c', 'долгое hː', lambda s: s.replace('h', 'hː')),
      ('d', 'звонкое ɦ (хинди)', lambda s: s.replace('h', 'ɦ'))]),
    ('m', 'конечное -aṁ: как «н»', '★ где конечное ṁ как в vadeyyuṁ',
     ['Tehi bhikkhūhi vatthu desetabbaṁ anārambhaṁ.', 'Bhedanasaṁvattanikaṁ vā adhikaraṇaṁ.', 'So bhikkhu yāvatatiyaṁ samanubhāsitabbo.'],
     [('a', 'как сейчас (ən)', lambda s: s),
      ('b', 'открытое ã (как ũ)', lambda s: re.sub('[əʌ]n' + END, 'a' + TILDE, s)),
      ('c', 'ə̃', lambda s: re.sub('[əʌ]n' + END, 'ə' + TILDE, s)),
      ('d', 'ə̃ + n', lambda s: re.sub('[əʌ]n' + END, 'ə' + TILDE + 'n', s))]),
    ('y', 'dhārayāmīti', '★ где «дхарайамити» правильно',
     ['Tasmā tuṇhī, evametaṁ dhārayāmīti.'],
     [('a', 'как сейчас (jj)', lambda s: s),
      ('b', 'одно j', lambda s: s.replace('ʌjjaːm', 'ʌjaːm'))]),
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
                s = fn(base) if callable(fn) else base
                assert vid == 'a' or not callable(fn) or s != base, (sid, vid, base)
                for take in (1, 2):
                    f = f'{sid}{i}.{vid}{take}.mp3'
                    vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': s})
                    if os.path.exists(f'{OUT}/{f}'):
                        continue
                    if not callable(fn) and fn[0] == 'carrier':
                        audio = carrier_cut(base)
                    else:
                        cfg = SynthesisConfig(length_scale=LENGTH * fn[1], noise_scale=0.6, noise_w_scale=0.7) if not callable(fn) else CFG
                        audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(s)), cfg)
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                                    '-q:a', '7', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)
            phrases.append({'id': f'{sid}{i}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title + ', 0.7x', 'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'r50', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
