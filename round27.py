"""Round 27: SN 12.2 words heard wrong - the long compound sokaparidevadukkhadomanassupāyāsā, -bhavo, paccayā
(round 18 made it paccayyā), Dutiyaṁ. Two takes each; own voice for reference.
Usage: .venv/bin/python round27.py -> out/r27/*.mp3, out/r27/index.json
"""
import json
import os
import re
import subprocess

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r27'
LENGTH = 1.15 / 0.875
SECTIONS = [
    ('soka', 'sokaparidevadukkhadomanassupāyāsā', '★ где длинное слово звучит целиком и разборчиво',
     ['Jarāmaraṇaṁ sokaparidevadukkhadomanassupāyāsā sambhavanti.'],
     [('a', 'как сейчас (одним словом)', lambda s: s),
      ('b', 'короткие паузы между частями', lambda s: s.replace('soːkʌpʌɾɪdeːʋʌdʊkkʰʌdoːmʌnʌssʊpaːjˈaːsaː', 'soːkʌ, pʌɾɪdeːʋʌ, dʊkkʰʌ, doːmʌnʌssʊ, paːjˈaːsaː')),
      ('c', 'ударения в каждой части', lambda s: s.replace('soːkʌpʌɾɪdeːʋʌdʊkkʰʌdoːmʌnʌssʊpaːjˈaːsaː', 'sˈoːkʌ pʌɾɪdˈeːʋʌ dˈʊkkʰʌ doːmˈʌnʌssʊ paːjˈaːsaː'))]),
    ('bhava', 'kāmabhavo, rūpabhavo, arūpabhavo', '★ где «-bhavo» звучит чисто: «бхаво»',
     ['Kāmabhavo, rūpabhavo, arūpabhavo.'],
     [('a', 'как сейчас (ʋ)', lambda s: s),
      ('b', 'v вместо ʋ', lambda s: s.replace('bʰʌʋoː', 'bʰʌvoː')),
      ('c', 'ударение на «bha»', lambda s: s.replace('ˈaːmʌbʰʌʋoː', 'aːmʌbʰˈʌʋoː').replace('ˈuːpʌbʰʌʋoː', 'uːpʌbʰˈʌʋoː'))]),
    ('pacc', 'saṅkhārapaccayā', '★ где «paccayā» звучит «паччайя» без лишнего',
     ['Avijjāpaccayā saṅkhārā, saṅkhārapaccayā viññāṇaṁ.'],
     [('a', 'как сейчас (удвоенное y: jj)', lambda s: s),
      ('b', 'одно y', lambda s: s.replace('ʌccʌjjaː', 'ʌccʌjaː'))]),
    ('dut', 'Dutiyaṁ', '★ где «dutiyaṁ» звучит «дутийам»',
     ['Dutiyaṁ jhānaṁ upasampajja viharati.'],
     [('a', 'как сейчас (jj)', lambda s: s),
      ('b', 'одно y', lambda s: s.replace('tɪjjʌŋŋ', 'tɪjʌŋŋ')),
      ('c', 'одно y + конечное m', lambda s: s.replace('tɪjjʌŋŋ', 'tɪjʌm'))]),
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
    json.dump({'round': 'r27', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
