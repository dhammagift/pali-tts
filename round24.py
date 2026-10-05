"""Round 24: what round 23 left - final ṁ (dukkhaṁ "дуккхан"), viharati ("вихарти" since the open-a
rule is off), sahagatā ("сахгата"), nimmānaratī ("ra" lost). Two takes each; own voice for reference.
Usage: .venv/bin/python round24.py -> out/r24/*.mp3, out/r24/index.json
"""
import json
import os
import re
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r24'
LENGTH = 1.15 / 0.875
FINAL_M = re.compile(r'([ʌaeoiuɪʊ]ː?)ŋŋ(?=[ ,.?!:;]|$)')
END = r'(?=[ ,.?!:;]|$)'
SECTIONS = [
    ('m', 'конечное ṁ: dukkhaṁ → «дуккхан»', '★ где конечное ṁ звучит как носовое «м/нг», а не «н» (dukkhaṁ, imasmiṁ, cakkhuṁ)',
     ['Jarāpi dukkhā, maraṇampi dukkhaṁ.', 'Atthi imasmiṁ kāye.', 'Cakkhuṁ udapādi, ñāṇaṁ udapādi.'],
     [('a', 'как сейчас (ŋŋ)', lambda s: s),
      ('b', 'одно ŋ', lambda s: FINAL_M.sub(r'\1ŋ', s)),
      ('c', 'm', lambda s: FINAL_M.sub(r'\1m', s)),
      ('d', 'носовая гласная (ʌ̃)', lambda s: FINAL_M.sub('\\1\u0303', s))]),
    ('vih', 'viharati → «вихарти»', '★ где «viharati» звучит полностью: «вихарати»',
     ['Paṭhamaṁ jhānaṁ upasampajja viharati.', 'Ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'открытое «а» в окончании -ati', lambda s: re.sub('ʌ(?=tɪ' + END + ')', 'a', s)),
      ('c', 'удвоенное r (ɾɾ)', lambda s: s.replace('hˈʌɾʌtɪ', 'hˈʌɾɾʌtɪ')),
      ('d', 'раскатистое r', lambda s: s.replace('hˈʌɾʌtɪ', 'hˈʌrʌtɪ'))]),
    ('saha', 'sahagatā → «сахгата»', '★ где «sahagatā» звучит «сахагата»',
     ['Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'долгое ударное (hˈʌː)', lambda s: s.replace('sʌhˈʌɡ', 'sʌhˈʌːɡ')),
      ('c', 'звонкое h (ɦ)', lambda s: s.replace('sʌhˈʌɡ', 'sʌɦˈʌɡ')),
      ('d', 'удвоенное g', lambda s: s.replace('sʌhˈʌɡʌ', 'sʌhˈʌɡɡʌ'))]),
    ('nimma', 'nimmānaratī: «ra» пропадает', '★ где «nimmānaratī» звучит полностью: «нимманарати»',
     ['Nimmānaratī devā saddamanussāvesuṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'удвоенное r (ɾɾ)', lambda s: s.replace('nʌɾʌtiː', 'nʌɾɾʌtiː')),
      ('c', 'раскатистое r', lambda s: s.replace('nʌɾʌtiː', 'nʌrʌtiː')),
      ('d', 'ударение на «ra»', lambda s: s.replace('nɪmmˈaːnʌɾʌtiː', 'nɪmmaːnʌɾˈʌtiː'))]),
]


def render(v, ipa, length, f):
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-q:a', '7', f], input=audio.tobytes(), check=True)


if __name__ == '__main__':
    pratham = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    own = PiperVoice.load('models/pali_dg-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, note, texts, variants in SECTIONS:
        phrases = []
        for n, text in enumerate(texts):
            base = tune(to_ipa(text, full_a=True))
            vs = []
            for vid, label, fn in variants:
                assert vid == 'a' or fn(base) != base, (sid, vid, base)  # a variant that changes nothing is a bug
                for take in (1, 2):
                    f = f'{sid}{n}.{vid}{take}.mp3'
                    render(pratham, fn(base), LENGTH, f'{OUT}/{f}')
                    vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': fn(base)})
            render(own, to_ipa(text, full_a=True), 1.0 / 0.875, f'{OUT}/{sid}{n}.own.mp3')
            vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'{sid}{n}.own.mp3', 'sent': ''})
            phrases.append({'id': f'{sid}{n}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title, 'multi_best': False, 'phrases': phrases})
        print(sid, flush=True)
    json.dump({'round': 'r24', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
