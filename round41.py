"""Round 41: two things heard wrong again on the site (r30). diṭṭhupādānaṁ read as «диччупадана» (round 20 asked
about ṭṭh on sammādiṭṭhi; the long ʈːʰ got two «best» there but was not adopted) and saṅkhārapaccayā as
«санкхарпаччая», the a after r swallowed (round 28: open a ok/bad, long ʌː bad). New spellings only, plus ʈːʰ again
on the new word. 0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round41.py -> out/r41/; then build_page.py with ROUND = 'r41'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r41'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('tth', 'diṭṭhupādānaṁ: «диччупадана»', '★ где «диттхупадана», без «ч»',
     ['Kāmupādānaṁ diṭṭhupādānaṁ sīlabbatupādānaṁ attavādupādānaṁ.'],
     [('a', 'как сейчас (ʈʈʰ)', lambda s: s),
      ('b', 'долгое ʈːʰ (лучшее в r20 на sammādiṭṭhi)', word('dɪʈʈʰʊ', 'dɪʈːʰʊ')),
      ('c', 'придыхание отдельным h', word('dɪʈʈʰʊ', 'dɪʈʈhʊ')),
      ('d', 'полное u после ṭṭh', word('dɪʈʈʰʊ', 'dɪʈʈʰu')),
      ('e', 'ударение на di', word('dɪʈʈʰʊ', 'dˈɪʈʈʰʊ'))]),
    ('sankh', 'saṅkhārapaccayā: «санкхарпаччая»', '★ где слышно «санкхАРА-паччая»',
     ['Avijjāpaccayā saṅkhārā, saṅkhārapaccayā viññāṇaṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'ударение на khā (как у отдельного слова)', word('sʌŋkʰaːɾʌp', 'sʌŋkʰˈaːɾʌp')),
      ('c', 'два слова: saṅkhāra paccayā', word('sʌŋkʰaːɾʌpˈ', 'sʌŋkʰˈaːɾʌ pˈ')),
      ('d', 'долгое aː после r', word('sʌŋkʰaːɾʌp', 'sʌŋkʰaːɾaːp')),
      ('e', 'ударение на khā + открытое a после r', word('sʌŋkʰaːɾʌp', 'sʌŋkʰˈaːɾap'))]),
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
    json.dump({'round': 'r41', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
