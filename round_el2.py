"""Round el2 (owner 2026-10-28: el1's voices read without our rules - give them our rules): ElevenLabs v4 reads IPA
written between slashes, so each word goes as /our IPA/ (to_ipa(full_a=True) as the server, without pratham's tune).
Lines: the ones the old rounds kept failing on (ṁ, ṭṭh, final -o, swallowed a, a word alone, paggayha, ph, vimucciṁsūti),
3 voices of el1 against pratham as in DG (0.7x). Blind.
Usage (on f3): .venv/bin/python round_el2.py -> out/el2/; then build_page.py with ROUND = 'el2'
"""
import base64
import json
import os
import re
import urllib.request

from pali_ipa import to_ipa
from round_el1 import VOICES, add_to_library, api

OUT = 'out/el2'
NAMES = ['Taksh', 'Kunal', 'Raghav']
TEXTS = [  # (text, the rounds it failed in)
    ('Jarāpi dukkhā, maraṇampi dukkhaṁ.', 'r20–26: dukkhaṁ «дуккхан», jarā'),
    ('Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.', 'r21–28: Yāyaṁ, ponobbhavikā «бхарика», sahagatā «сахгата»'),
    ('Paṭhamaṁ jhānaṁ upasampajja viharati.', 'r22–25: viharati «вихарти», Paṭhamaṁ'),
    ('Paṭhamaṁ.', 'r27–30, r55: слово отдельно'),
    ('Avijjāpaccayā saṅkhārā, saṅkhārapaccayā viññāṇaṁ.', 'r27, r28, r41: «санкхарпаччая», viññāṇaṁ'),
    ('Tiṭṭhatu, bhikkhave, ekaṁ vassaṁ.', 'r46–49: ṭṭh «чичату»'),
    ('Uddiṭṭhaṁ kho āyasmanto nidānaṁ.', 'r49, r52: ṭṭh, -aṁ'),
    ('Ātāpī sampajāno satimā.', 'r38–40: конечное -o короткое'),
    ('Itipi so bhagavā arahaṁ sammāsambuddho vijjācaraṇasampanno sugato lokavidū.', 'r31–32, r37: arahaṁ, sugato'),
    ('Samādāya paggayha aṭṭhāsi.', 'r50–54: «пагейа»'),
    ('Tasmā tuṇhī, evametaṁ dhārayāmīti.', 'r50, r52: «дхареямити»'),
    ('Dukkhanirodhagāminiyā paṭipadāya ñāṇaṁ.', 'r46–47: «гаминья», «пратипада»'),
    ('Rasavitakko loke, phoṭṭhabbavitakko loke.', 'r46–47: phoṭṭhabba'),
    ('Tikkhattuṁ padakkhiṇaṁ katvā.', 'r53–54: tikkhattuṁ без i и ṁ'),
    ('Tasmātiha, bhikkhave, yogo karaṇīyo.', 'r37–39: не слышно -ha'),
    ('Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.',
     'r56–57: vimucciṁsūti «чиксути»'),
]


def slashed(text):
    """Every word as /IPA/ (v4 reads IPA between slashes), punctuation left outside."""
    return re.sub(r"[^\s,.;:!?—]+", lambda m: '/' + m.group(0) + '/', to_ipa(text, full_a=True))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    ids = {n: v for v, n in VOICES.items()}
    phrases = []
    for i, (text, why) in enumerate(TEXTS):
        vs = []
        f = f'p{i}.pratham.mp3'
        if not os.path.exists(f'{OUT}/{f}'):
            r = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': 'pratham', 'rate': 0.7}).encode(),
                                       {'Content-Type': 'application/json'})
            open(f'{OUT}/{f}', 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(r))['audioContent']))
        vs.append({'id': 'pratham', 'label': 'pratham (DG сейчас)', 'file': f, 'sent': text})
        for name in NAMES:
            f = f'p{i}.{name}.mp3'
            if not os.path.exists(f'{OUT}/{f}'):
                add_to_library(ids[name])
                open(f'{OUT}/{f}', 'wb').write(api(f'/v1/text-to-speech/{ids[name]}?output_format=mp3_44100_128',
                                                   {'text': slashed(text), 'model_id': 'eleven_v4'}))
            vs.append({'id': name, 'label': f'EL v4 {name}', 'file': f, 'sent': text})
        phrases.append({'id': f'p{i}', 'text': text, 'ipa': slashed(text), 'script': '', 'variants': vs,
                        'note': f'Было: {why}. ★ лучший; ✓ правильно; ✗ неправильно. На слово с ошибкой можно нажать'})
        print(i, flush=True)
    json.dump({'round': 'el2', 'title': 'ElevenLabs v4 с нашими правилами',
               'intro': 'Голоса ElevenLabs (модель v4) читают не текст, а наш IPA — те же правила, что у pratham. '
                        'Фразы — те, на которых спотыкались старые раунды. Рядом pratham, как сейчас в DG (0.7x). Вслепую.',
               'sections': [{'id': 'p', 'title': 'Пали: нерешённые места', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
