"""Round el3 (owner 2026-10-29: «делай», after el2's ASR check): our IPA is written for Piper (c, ɟ, ʌ, bʰ), which
ElevenLabs reads by the IPA standard - el2 had short a as «о», c/j as k/y, ph/bh as p/b. Here the same rules with
standard symbols (el_ipa): c -> t͡ʃ, ɟ -> d͡ʒ, ʌ -> ə, voiced aspirates ʱ. 4 lines with those sounds, one voice (limits).
Usage (on f3): .venv/bin/python round_el3.py -> out/el3/; then build_page.py with ROUND = 'el3'
"""
import base64
import json
import os
import re
import urllib.request

from pali_ipa import to_ipa
from round_el1 import VOICES, api

OUT = 'out/el3'
NAME = 'Taksh'
TEXTS = [('Avijjāpaccayā saṅkhārā, saṅkhārapaccayā viññāṇaṁ.', 'el2: a как «о», paccayā «бакхоя»'),
         ('Rasavitakko loke, phoṭṭhabbavitakko loke.', 'el2: ph как p'),
         ('Ātāpī sampajāno satimā.', 'el2: j как y'),
         ('Jarāpi dukkhā, maraṇampi dukkhaṁ.', 'el2: maraṇa «морно»')]


def el_ipa(ipa):
    """Piper-style IPA -> standard IPA for ElevenLabs v4."""
    ipa = ipa.replace('cc', 'tt͡ʃ').replace('ɟɟ', 'dd͡ʒ').replace('c', 't͡ʃ').replace('ɟ', 'd͡ʒ').replace('ʌ', 'ə')
    return re.sub(r'([bdɡɖʒ])ʰ', r'\1ʱ', ipa)


def slashed(text):
    return re.sub(r"[^\s,.;:!?—]+", lambda m: '/' + m.group(0) + '/', el_ipa(to_ipa(text, full_a=True)))


if __name__ == '__main__':
    assert el_ipa('pˈʌccʌjaː ɟʌɾˈaː bʰˈɪkkʰʌ') == 'pˈətt͡ʃəjaː d͡ʒəɾˈaː bʱˈɪkkʰə', el_ipa('pˈʌccʌjaː ɟʌɾˈaː bʰˈɪkkʰʌ')
    os.makedirs(OUT, exist_ok=True)
    vid = next(v for v, n in VOICES.items() if n == NAME)
    phrases = []
    for i, (text, why) in enumerate(TEXTS):
        vs = []
        f = f'p{i}.pratham.mp3'
        if not os.path.exists(f'{OUT}/{f}'):
            r = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': 'pratham', 'rate': 0.7}).encode(),
                                       {'Content-Type': 'application/json'})
            open(f'{OUT}/{f}', 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(r))['audioContent']))
        vs.append({'id': 'pratham', 'label': 'pratham (DG сейчас)', 'file': f, 'sent': text})
        f = f'p{i}.{NAME}.mp3'
        if not os.path.exists(f'{OUT}/{f}'):
            open(f'{OUT}/{f}', 'wb').write(api(f'/v1/text-to-speech/{vid}?output_format=mp3_44100_128',
                                               {'text': slashed(text), 'model_id': 'eleven_v4'}))
        vs.append({'id': NAME, 'label': f'EL v4 {NAME}, стандартный IPA', 'file': f, 'sent': text})
        phrases.append({'id': f'p{i}', 'text': text, 'ipa': slashed(text), 'script': '', 'variants': vs,
                        'note': f'{why}. ★ лучший; ✓ правильно; ✗ неправильно. На слово с ошибкой можно нажать'})
        print(i, slashed(text), flush=True)
    json.dump({'round': 'el3', 'title': 'ElevenLabs v4: наш IPA в стандартных знаках',
               'intro': 'Те же наши правила, но c, j, короткое a и придыхание записаны стандартными знаками IPA '
                        '(в el2 голос читал их по-своему). Один голос, 4 фразы, рядом pratham (0.7x). Вслепую.',
               'sections': [{'id': 'p', 'title': 'Пали: c, j, a, ph', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
