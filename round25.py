"""Round 25: more SN 56.11 words heard wrong - paccaññāsiṁ, appaṭivattiyaṁ, kiñci, muhuttena, Paṭhamaṁ.
Two takes each; own voice for reference.
Usage: .venv/bin/python round25.py -> out/r25/*.mp3, out/r25/index.json
"""
import json
import os
import re
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r25'
LENGTH = 1.15 / 0.875
FINAL_M = re.compile(r'([ʌaeoiuɪʊ]ː?)ŋŋ(?=[ ,.?!:;]|$)')
SECTIONS = [
    ('pacc', 'paccaññāsiṁ', '★ где «paccaññāsiṁ» звучит полностью и чисто',
     ['Anuttaraṁ sammāsambodhiṁ abhisambuddho paccaññāsiṁ.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'конечное -iṁ как «im»', lambda s: s.replace('ˈaːsɪŋŋ', 'ˈaːsɪm')),
      ('c', 'напряжённое i в конце (iŋŋ)', lambda s: s.replace('ˈaːsɪŋŋ', 'ˈaːsiŋŋ')),
      ('d', 'одно c (pʌcʌ…)', lambda s: s.replace('pʌccʌɲːj', 'pʌcʌɲːj'))]),
    ('appa', 'appaṭivattiyaṁ', '★ где «appaṭivattiyaṁ» звучит полностью',
     ['Dhammacakkaṁ pavattitaṁ appaṭivattiyaṁ samaṇena vā brāhmaṇena vā.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'одно y (без jj)', lambda s: s.replace('ʋˈʌttɪjjʌŋŋ', 'ʋˈʌttɪjʌŋŋ')),
      ('c', 'конечное m', lambda s: s.replace('ʋˈʌttɪjjʌŋŋ', 'ʋˈʌttɪjjʌm')),
      ('d', 'удвоенное ṭ', lambda s: s.replace('ʌppʌʈɪ', 'ʌppʌʈʈɪ'))]),
    ('kinci', 'kiñci', '★ где «kiñci» звучит как «кинчи»',
     ['Yaṁ kiñci samudayadhammaṁ sabbaṁ taṁ nirodhadhammanti.'],
     [('a', 'как сейчас (ɲc)', lambda s: s),
      ('b', 'n вместо ñ (nc)', lambda s: s.replace('kˈɪɲcɪ', 'kˈɪncɪ')),
      ('c', 'напряжённое i (kiɲ)', lambda s: s.replace('kˈɪɲcɪ', 'kˈiɲcɪ')),
      ('d', 'удвоенное c', lambda s: s.replace('kˈɪɲcɪ', 'kˈɪɲccɪ'))]),
    ('muhu', 'muhuttena', '★ где «muhuttena» звучит полностью: «мухуттена»',
     ['Iti ha tena khaṇena tena muhuttena yāva brahmalokā saddo abbhuggacchi.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'звонкое h (ɦ)', lambda s: s.replace('mʊhʊtt', 'mʊɦʊtt')),
      ('c', 'напряжённое u (muhu)', lambda s: s.replace('mʊhʊtt', 'muhutt')),
      ('d', 'ударение на «hu»', lambda s: s.replace('mʊhʊttˈeː', 'mʊhˈʊtteː'))]),
    ('patha', 'Paṭhamaṁ', '★ где «paṭhamaṁ» звучит «патхамам», а не «патхана»',
     ['Paṭhamaṁ jhānaṁ upasampajja viharati.'],
     [('a', 'как сейчас', lambda s: s),
      ('b', 'конечное m', lambda s: s.replace('pˈʌʈʰʌmʌŋŋ', 'pˈʌʈʰʌmʌm')),
      ('c', 'удвоенное m (mm)', lambda s: s.replace('pˈʌʈʰʌmʌŋŋ', 'pˈʌʈʰʌmmʌŋŋ')),
      ('d', 'удвоенное ṭh', lambda s: s.replace('pˈʌʈʰʌmʌŋŋ', 'pˈʌʈʈʰʌmʌŋŋ'))]),
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
    json.dump({'round': 'r25', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
