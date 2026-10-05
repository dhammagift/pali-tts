"""Round 28: what rounds 24-27 left - saṅkhāra ("санкхарпаччая", the a after r swallowed), sahagatā, a title word
said alone (Dutiyaṁ / Paṭhamaṁ worse than inside a sentence), sammāsambodhiṁ abhisambuddho'ti ("с натяжкой";
'ti is cut off as a separate word), word-final -uṁ (cakkhuṁ, -suṁ: every variant of r24 was bad).
Two takes each, blind; own voice for reference. Pre-checked with ears (ears.py) before the page goes out.
Usage: .venv/bin/python round28.py -> out/r28/*.mp3, out/r28/index.json
"""
import json
import os
import re

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune
from round26 import render, synth_cut

OUT = 'out/r28'
END = r'(?=[ ,.?!:;]|$)'
UM = re.compile('ʊŋŋ' + END)


def cut_final(stop):
    """-uṁ as ŋ + stop, the stop cut out of the audio (round 26's trick for -aṁ)."""
    def fn(s):
        s = UM.sub('ʊŋ' + stop, s)
        idx = [i for i in range(1, len(s)) if s[i] == stop and s[i - 1] == 'ŋ' and (i + 1 == len(s) or s[i + 1] in ' ,.?!:;')]
        return s, idx
    return fn


def plain(f):
    return lambda s: (f(s), [])


SECTIONS = [
    ('sankh', 'saṅkhāra: «санкхарпаччая»', '★ где слышно «санкхАРА-паччая», а не «санкхарпаччая»',
     ['Avijjāpaccayā saṅkhārā, saṅkhārapaccayā viññāṇaṁ.'],
     [('a', 'как сейчас', plain(lambda s: s)),
      ('b', 'открытое «а» после r', plain(lambda s: s.replace('kʰaːɾʌpˈʌcc', 'kʰaːɾapˈʌcc'))),
      ('c', 'долгое «а» после r', plain(lambda s: s.replace('kʰaːɾʌpˈʌcc', 'kʰaːɾʌːpˈʌcc')))]),
    ('saha', 'sahagatā', '★ где «sahagatā» звучит «сахагата»',
     ['Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.'],
     [('a', 'как сейчас', plain(lambda s: s)),
      ('b', 'долгое ударное (hˈʌː), r24: ok/ok', plain(lambda s: s.replace('sʌhˈʌɡ', 'sʌhˈʌːɡ'))),
      ('c', 'открытое ударное «а»', plain(lambda s: s.replace('sʌhˈʌɡ', 'sʌhˈaɡ')))]),
    ('title', 'отдельное слово (заголовок)', '★ где слово звучит так же чисто, как внутри фразы',
     ['Dutiyaṁ', 'Paṭhamaṁ', 'Tatiyaṁ'],
     [('a', 'как сейчас', plain(lambda s: s)),
      ('b', 'с точкой в конце', plain(lambda s: s + '.')),
      ('c', 'пауза до и точка после', plain(lambda s: ', ' + s + '.'))]),
    ('abhi', 'sammāsambodhiṁ abhisambuddho’ti', '★ где обе слова звучат естественно, «абхисамбуддхоти»',
     ['Anuttaraṁ sammāsambodhiṁ abhisambuddho’ti paccaññāsiṁ.'],
     [('a', 'как сейчас (’ti отдельным словом)', plain(lambda s: s)),
      ('b', '’ti слитно', plain(lambda s: s.replace('ʊddʰoː tˈɪ', 'ʊddʰoːtɪ'))),
      ('c', '’ti слитно, ударение на «dho»', plain(lambda s: s.replace('sʌmbˈʊddʰoː tˈɪ', 'sʌmbʊddʰˈoːtɪ')))]),
    ('um', 'конечное -uṁ (cakkhuṁ, -suṁ)', '★ где конечное ṁ звучит носовым «нг», не «су», не «сун», не «сум»',
     ['Cakkhuṁ udapādi.', 'Brahmakāyikā devā saddamanussāvesuṁ.'],
     [('a', 'как сейчас (ŋŋ)', plain(lambda s: s)),
      ('b', 'ŋɡ целиком (как -aṁ)', plain(lambda s: UM.sub('ʊŋɡ', s))),
      ('c', 'ŋɡ, «г» вырезано', cut_final('ɡ')),
      ('d', 'ŋk, «к» вырезано', cut_final('k'))]),
]

if __name__ == '__main__':
    own = PiperVoice.load('models/pali_dg-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for sid, title, note, texts, variants in SECTIONS:
        phrases = []
        for n, text in enumerate(texts):
            base = tune(to_ipa(text, full_a=True))
            vs = []
            for vid, label, fn in variants:
                s, cut = fn(base)
                assert vid == 'a' or s != base, (sid, vid, base)  # a variant that changes nothing is a bug
                for take in (1, 2):
                    f = f'{sid}{n}.{vid}{take}.mp3'
                    render(synth_cut(list(s), cut), f'{OUT}/{f}')
                    vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': s})
            audio = own.phoneme_ids_to_audio(own.phonemes_to_ids(list(to_ipa(text, full_a=True))),
                                             SynthesisConfig(length_scale=1.0 / 0.875, noise_scale=0.6, noise_w_scale=0.7))
            render(audio, f'{OUT}/{sid}{n}.own.mp3')
            vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'{sid}{n}.own.mp3', 'sent': ''})
            phrases.append({'id': f'{sid}{n}', 'text': text, 'ipa': base, 'script': '', 'variants': vs, 'note': note})
        sections.append({'id': sid, 'title': title, 'multi_best': False, 'phrases': phrases})
        print(sid, flush=True)
    json.dump({'round': 'r28', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
