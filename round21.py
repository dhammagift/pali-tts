"""Round 21: words the owner heard wrong in SN 56.11 - ponobbhavikā ('бхарика'), taṇhāya ('тахая'),
ñāṇaṁ ('ньан'), paññā ('падья'), tiparivaṭṭaṁ ('тэпариваттан'), Ñāṇañca ('янанча'). A few IPA variants for pratham each, two takes; own voice for reference.
Usage: .venv/bin/python round21.py -> out/r21/*.mp3, out/r21/index.json
"""
import json
import os
import re
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r21'
LENGTH = 1.15 / 0.875
SECTIONS = [
    ('ponob', 'ponobbhavikā: «бхарика»', '★ где «ponobbhavikā» звучит полностью: «понобхавика»',
     ['Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'без открытого «а» (bʰʌʋ)', lambda s: s.replace('obbʰaʋ', 'obbʰʌʋ')),
      ('c', 'ударение на первый слог (ˈpoː)', lambda s: s.replace('poːnˈobbʰ', 'pˈoːnobbʰ')),
      ('d', 'v вместо ʋ', lambda s: s.replace('obbʰaʋ', 'obbʰav'))]),
    ('tanha', 'taṇhāya: «тахая»', '★ где слышно «н» в «taṇhā»: «танха», а не «таха»',
     ['Taṇhāya nirodhā upādānanirodho.', 'Taṇhāya ca virāgā.'],
     [('a', 'как сейчас (ɳh)', lambda s: s),
      ('b', 'удвоенное ɳɳh', lambda s: s.replace('ɳh', 'ɳɳh')),
      ('c', 'без открытого «а» перед ɳ (tʌɳh)', lambda s: s.replace('taɳh', 'tʌɳh')),
      ('d', 'звонкое h (ɳɦ)', lambda s: s.replace('ɳh', 'ɳɦ'))]),
    ('nanam', 'ñāṇaṁ: «ньан»', '★ где «ñāṇaṁ» звучит полностью: «ньянам/ньянанг»',
     ['Cakkhuṁ udapādi, ñāṇaṁ udapādi, paññā udapādi.'],
     [('a', 'как сейчас (ɳʌŋŋ)', lambda s: s),
      ('b', 'удвоенное ɳɳ', lambda s: s.replace('ˈaːɳʌŋŋ', 'ˈaːɳɳʌŋŋ')),
      ('c', 'конечное m (ɳʌm)', lambda s: s.replace('ɳʌŋŋ', 'ɳʌm')),
      ('d', 'пауза после слова', lambda s: s.replace('ɳʌŋŋ ', 'ɳʌŋŋ, '))]),
    ('panna', 'paññā: «падья»', '★ где «paññā» звучит «паннья», а не «падья»',
     ['Cakkhuṁ udapādi, ñāṇaṁ udapādi, paññā udapādi.', 'Sīlaṁ samādhi paññā vimutti.'],
     [('a', 'как сейчас (ɲːj)', lambda s: s),
      ('b', 'двойное ɲɲ', lambda s: s.replace('ɲːj', 'ɲɲ')),
      ('c', 'n + ɲ (nɲ)', lambda s: s.replace('ɲːj', 'nɲ')),
      ('d', 'nnj (как «ннь»)', lambda s: s.replace('ɲːj', 'nnj'))]),
    ('tipari', 'tiparivaṭṭaṁ: «тэпариваттан»', '★ где «ti» звучит как «ти», а не «тэ», и слово целиком',
     ['Evaṁ tiparivaṭṭaṁ dvādasākāraṁ yathābhūtaṁ ñāṇadassanaṁ.'],
     [('a', 'как сейчас (ɪ)', lambda s: s),
      ('b', 'i вместо ɪ в «ti»', lambda s: s.replace('tɪpaɾɪ', 'tipaɾɪ')),
      ('c', 'i вместо ɪ во всех кратких i', lambda s: s.replace('ɪ', 'i')),
      ('d', 'i в «ti» + конечное m', lambda s: s.replace('tɪpaɾɪʋˈʌʈʈʌŋŋ', 'tipaɾɪʋˈʌʈʈʌm'))]),
    ('nana', 'Ñāṇañca: «янанча»', '★ где начальное «ñ» звучит как «нь», а не «я»',
     ['Ñāṇañca pana me dassanaṁ udapādi.'],
     [('a', 'как сейчас (ɲj)', lambda s: s),
      ('b', 'просто ɲ', lambda s: re.sub(r'^ɲj', 'ɲ', s)),
      ('c', 'n + j (nj)', lambda s: re.sub(r'^ɲj', 'nj', s)),
      ('d', 'долгое ɲː', lambda s: re.sub(r'^ɲj', 'ɲː', s))]),
]
pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
own = PiperVoice.load('models/pali_dg-medium.onnx')
os.makedirs(OUT, exist_ok=True)


def render(v, ipa, length, f):
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-q:a', '7', f], input=audio.tobytes(), check=True)


sections = []
for sid, title, note, texts, variants in SECTIONS:
    phrases = []
    for n, text in enumerate(texts):
        base = tune(to_ipa(text, full_a=True))
        vs = []
        for vid, label, fn in variants:
            assert vid == 'a' or fn(base) != base or len(texts) > 1, (sid, vid, base)  # a variant that changes nothing is a bug
            for take in (1, 2):
                f = f'{sid}{n}.{vid}{take}.mp3'
                render(pratham, fn(base), LENGTH, f'{OUT}/{f}')
                vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': fn(base)})
        render(own, to_ipa(text, full_a=True), 1.0 / 0.875, f'{OUT}/{sid}{n}.own.mp3')
        vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'{sid}{n}.own.mp3', 'sent': ''})
        phrases.append({'id': f'{sid}{n}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
    sections.append({'id': sid, 'title': title, 'multi_best': False, 'phrases': phrases})
    print(sid, flush=True)
json.dump({'round': 'r21', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
