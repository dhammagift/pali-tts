"""Round 42: DN 22 as heard in the app (r30 rules + ṭṭh as ʈːʰ and saṅkhāra- with aː from rounds 20/41):
pana before a comma «пан», bhamakārantevāsī «рнтеваси» (the a after r again), añchanto/añchāmī without «нь»,
ṭhito/ṭhite «чито» (single ṭh), niṭṭhitaṁ «ничитан» (check of the new ʈːʰ), sutte «сутее» (should be short).
0.7x, 2 takes, blind.
Usage (on f3): .venv/bin/python round42.py -> out/r42/; then build_page.py with ROUND = 'r42'
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round31 import SR

OUT = 'out/r42'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)


def word(old, new):
    def f(s):
        assert s.count(old) == 1, (old, s)
        return s.replace(old, new)
    return f


SECTIONS = [
    ('pana', 'pana перед запятой: «пан»', '★ где слышно «пана»',
     ['Kathañca pana, bhikkhave, bhikkhu kāye kāyānupassī viharati?'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое a в конце', word('pˈʌnʌ,', 'pˈʌna,')),
      ('c', 'долгое aː в конце', word('pˈʌnʌ,', 'pˈʌnaː,')),
      ('d', 'долгое ʌː в конце', word('pˈʌnʌ,', 'pˈʌnʌː,'))]),
    ('kara', 'bhamakārantevāsī: «рнтеваси»', '★ где слышно «бхамакАРАнтевāсӣ»',
     ['Dakkho bhamakāro vā bhamakārantevāsī vā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'долгое aː после r (как победило в saṅkhāra-)', word('kaːɾʌnteː', 'kaːɾaːnteː')),
      ('c', 'открытое a после r', word('kaːɾʌnteː', 'kaːɾanteː')),
      ('d', 'ударение на kā', word('bʰʌmʌkaːɾʌnteː', 'bʰʌmʌkˈaːɾʌnteː'))]),
    ('nch', 'añchanto, añchāmī: без «нь»', '★ где слышно мягкое «нь»: «аньчханто»',
     ['Dīghaṁ vā añchanto ‘dīghaṁ añchāmī’ti pajānāti.'],
     [('a', 'как сейчас (n)', lambda s: s),
      ('b', 'ɲ', lambda s: s.replace('ʌncʰ', 'ʌɲcʰ')),
      ('c', 'n + j (как в ñāṇa)', lambda s: s.replace('ʌncʰ', 'ʌnjcʰ')),
      ('d', 'ɲ + j', lambda s: s.replace('ʌncʰ', 'ʌɲjcʰ'))]),
    ('th', 'ṭhito, ṭhite: «чито»', '★ где «тхито», без «ч»',
     ['Ṭhito vā ‘ṭhitomhī’ti pajānāti.', 'Gate ṭhite nisinne sutte jāgarite.'],
     [('a', 'как сейчас (ʈʰ)', lambda s: s),
      ('b', 'долгое ʈːʰ (как в ṭṭh)', lambda s: s.replace('ʈʰ', 'ʈːʰ')),
      ('c', 'придыхание отдельным h', lambda s: s.replace('ʈʰ', 'ʈh')),
      ('d', 'напряжённое i после ṭh', lambda s: s.replace('ʈʰɪ', 'ʈʰi').replace('ʈʰˈɪ', 'ʈʰˈi'))]),
    ('tth', 'niṭṭhitaṁ: «ничитан» (уже с новым ʈːʰ)', '★ где «ниттхитам», без «ч»',
     ['Ānāpānapabbaṁ niṭṭhitaṁ.'],
     [('a', 'как сейчас (новое ʈːʰ)', lambda s: s),
      ('b', 'ʈːʰ + напряжённое i', word('ʈːʰɪ', 'ʈːʰi')),
      ('c', 'ʈː + отдельное h', word('ʈːʰɪ', 'ʈːhɪ'))]),
    ('e', 'sutte: «сутее»', '★ где e короткое: «сутте»',
     ['Gate ṭhite nisinne sutte jāgarite.'],
     [('a', 'как сейчас (eː)', lambda s: s),
      ('b', 'короткое e', word('sˈʊtteː', 'sˈʊtte')),
      ('c', 'короткое открытое ɛ', word('sˈʊtteː', 'sˈʊttɛ'))]),
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
    json.dump({'round': 'r42', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
