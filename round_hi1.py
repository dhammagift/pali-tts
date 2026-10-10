"""Round hi1: Pali spelled the way pratham's own training data spells Hindi (owner: «Hindi is a big living language, it
must have these sounds - find the equivalents»). pratham learned from espeak-ng hi phonemes, and espeak writes Hindi
geminates its own way: पत्ता pˈʌtːaː, बच्चा bˈʌcːaː, पक्का pˈʌkːaː, अच्छा ˈʌcʰcʰaː, चिट्ठी cˈɪʈʰʈʰi, पत्थर pˈʌtʰːəɾ,
बुद्ध bˈʊdʰː - while our IPA writes tt, cc, kk, ccʰ, ʈːʰ, ttʰ, ddʰ, sequences the voice never saw. A word-final m:
तुम tˌʊm, हम hˌəm, कलम kˈʌləm; ṁ before v: संवाद sənʋˈaːd.
Blind on the pmix phrases: (a) now; (b) the geminates as in Hindi; (c) (b) + ṁ as Hindi's final m; (d) (b) + a final\nṁ as ʌn everywhere (owner: ahaṁ ˈʌhʌn reads right, evaṁ ˈeːʋən does not). 0.7x, 2 takes.
On top, for reference: the Hindi words themselves, read the normal Piper way (espeak hi -> pratham).
Usage (f3): .venv/bin/python round_hi1.py -> out/hi1/; then a build_page copy with ROUND = 'hi1'
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

sys.argv[1:] = ['-']  # round_pmix reads a model dir from argv; only its TEXTS are used
from round_pmix import TEXTS  # noqa: E402

OUT = 'out/hi1'
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)
END = r'(?=[ ,.?!:;]|$)'
# our geminate -> espeak hi's (checked on the Hindi words in HINDI: aspirates first)
GEMINATES = [('ʈːʰ', 'ʈʰʈʰ'), ('ʈʈʰ', 'ʈʰʈʰ'), ('ccʰ', 'cʰcʰ'), ('ttʰ', 'tʰː'), ('ddʰ', 'dʰː'),
             ('kk(?!ʰ)', 'kː'), ('ɡɡ(?!ʰ)', 'ɡː'), ('cc(?!ʰ)', 'cː'), ('ɟɟ(?!ʰ)', 'ɟː'), ('tt(?!ʰ)', 'tː'),
             ('dd(?!ʰ)', 'dː'), ('pp(?!ʰ)', 'pː')]
AHAM = [('ən' + END, 'ʌn')]  # owner: ahaṁ (ˈʌhʌn, round 31's full a) reads right, evaṁ (ˈeːʋən) does not
NIGGAHITA = [('(?<=h)ʌn' + END, 'ʌm'), ('ən' + END, 'əm'), ('u\u0303' + END, 'ʊm'), ('ʌŋʋ', 'ənʋ')]
HINDI = [('तुम', 'tum — как kātuṁ, tikkhattuṁ'), ('हम', 'ham — как -aṁ'), ('कलम', 'kalam — как -aṁ'),
         ('नहीं', 'nahīṁ — носовое на конце'), ('चिट्ठी', 'ciṭṭhī — как ṭṭh'), ('इकट्ठा', 'ikaṭṭhā — как ṭṭh'),
         ('अच्छा', 'acchā — как icchā'), ('पत्थर', 'patthar — как tth'), ('बुद्ध', 'buddh — как ddh'),
         ('संवाद', 'saṁvād — как asaṁvāso'), ('उन्हीं', 'unhīṁ — как tuṇhī'), ('अन्यत्र', 'anyatra — как aññatra')]


def subs(ipa, table):
    for rx, rep in table:
        ipa = re.sub(rx, rep, ipa)
    return ipa


def mp3(audio, f):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-q:a', '5', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)


if __name__ == '__main__':
    assert subs('sˈʌttʌ ʋɪttʰaːɾə bˈʊddʰʌ ɪccʰˈaː ʊddˈɪʈːʰən', GEMINATES) == 'sˈʌtːʌ ʋɪtʰːaːɾə bˈʊdʰːʌ ɪcʰcʰˈaː ʊdːˈɪʈʰʈʰən'
    assert subs('sˈʊtən. kˈaːtu\u0303, ʌsʌŋʋˈaːsoː mʌhʌn', NIGGAHITA) == 'sˈʊtəm. kˈaːtʊm, ʌsənʋˈaːsoː mʌhʌm'
    voice = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    say = lambda phonemes: voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(phonemes)), CFG)
    ref = []
    for i, (word, note) in enumerate(HINDI):
        ph = ''.join(sum(voice.phonemize(word), []))
        mp3(say(ph), f'h{i}.mp3')
        ref.append({'id': f'h{i}', 'text': word, 'ipa': ph, 'script': '', 'note': note + ' · оценивать не нужно',
                    'variants': [{'id': 'hi', 'label': 'хинди, обычное чтение Piper', 'file': f'h{i}.mp3', 'sent': ph}]})
    sections = [{'id': 'hi', 'title': 'Хинди: эти звуки голос говорит в своих словах', 'multi_best': True, 'phrases': ref}]
    for i, text in enumerate(TEXTS):
        a = tune(to_ipa(text, full_a=True))
        b = subs(a, GEMINATES)
        c = subs(b, NIGGAHITA)
        d = subs(b, AHAM)
        if a == c:
            continue  # nothing Hindi spells differently here
        vs = []
        for vid, label, ipa in (('a', 'как сейчас', a), ('b', 'удвоенные как в хинди', b), ('c', 'удвоенные + ṁ как в хинди', c),
                                ('d', 'удвоенные + ṁ как в ahaṁ (ʌn)', d)):
            if vid != 'a' and ipa == (a if vid == 'b' else b):
                continue  # nothing to change in this phrase
            for take in (1, 2):
                f = f'p{i}.{vid}{take}.mp3'
                mp3(say(ipa), f)
                vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': ipa})
        sections.append({'id': f'p{i}', 'title': f'Фраза {i + 1}: вслепую', 'multi_best': False, 'phrases': [
            {'id': f'p{i}', 'text': text, 'ipa': ' | '.join(dict.fromkeys([a, b, c, d])), 'script': '', 'variants': vs,
             'note': '★ где правильно'}]})
        print(text, '|', a, '|', b, '|', c)
    json.dump({'round': 'hi1', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(TEXTS), 'lines')
