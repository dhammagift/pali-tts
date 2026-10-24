"""Round pisa1 (owner 2026-10-23: «обучай санскритский, он звучит неприятно из-за тембра»): pali_sa - pratham fine-tuned on
Indic Parler's Sanskrit reading of 2350 Pali sentences, turned into pratham's timbre by kNN-VC (kaggle-pi-sa, 4 h) -
against pratham as DG reads now (our rules, the lone-word lead). pali_sa gets plain to_ipa (no tune(): those rules fix
pratham's Hindi habits). Its pace evened to pratham's at 0.7x (SA_LENGTH, measured: see __main__). Blind.
Usage (on f3): .venv/bin/python round_pisa1.py -> out/pisa1/; then build_page.py with ROUND = 'pisa1'
"""
import base64
import json
import os
import random
import re
import subprocess
import sys
import urllib.request

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa

OUT = 'out/pisa1'
SA = 'models/pali_sa-medium.onnx'
SA_LENGTH = float(sys.argv[1]) if len(sys.argv) > 1 else 1.15 / 0.7
TEXTS = ['Idamavoca bhagavā.',
         'Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.',
         'Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.',
         'Itthirūpaṁ, bhikkhave, purisassa cittaṁ pariyādāya tiṭṭhatī”ti.',
         'Paṭhamaṁ. Dutiyaṁ. Tatiyaṁ.',
         'Evaṁ me sutaṁ — ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.',
         'Cakkhuñca paṭicca rūpe ca uppajjati cakkhuviññāṇaṁ, tiṇṇaṁ saṅgati phasso.',
         'Jātipaccayā jarāmaraṇaṁ sokaparidevadukkhadomanassupāyāsā sambhavanti.',
         'Idha bhikkhu vivicceva kāmehi vivicca akusalehi dhammehi savitakkaṁ savicāraṁ vivekajaṁ pītisukhaṁ paṭhamaṁ jhānaṁ upasampajja viharati.',
         'Manopubbaṅgamā dhammā, manoseṭṭhā manomayā; manasā ce paduṭṭhena, bhāsati vā karoti vā.',
         'Yāyaṁ taṇhā ponobbhavikā nandirāgasahagatā tatratatrābhinandinī, seyyathidaṁ — kāmataṇhā, bhavataṇhā, vibhavataṇhā.',
         'Khīṇā jāti, vusitaṁ brahmacariyaṁ, kataṁ karaṇīyaṁ, nāparaṁ itthattāyāti pajānāti.']


def pratham(text):
    r = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': 'pratham', 'rate': 0.7}).encode(),
                               {'Content-Type': 'application/json'})
    return base64.b64decode(json.loads(urllib.request.urlopen(r, timeout=300).read())['audioContent'])


def pali_sa(voice, text, length):
    cfg = SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7)
    parts = []
    for sent in re.split(r'(?<=[.?!;:])\s+', text.strip()):
        parts += [voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(to_ipa(sent, full_a=True))), cfg), np.zeros(int(22050 * 0.35), np.float32)]
    a = np.concatenate(parts)
    return subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-', '-q:a', '7', '-f', 'mp3', '-'],
                          input=a.astype(np.float32).tobytes(), capture_output=True, check=True).stdout


def seconds(mp3):
    out = subprocess.run(['ffmpeg', '-i', '-', '-f', 'null', '-'], input=mp3, capture_output=True).stderr.decode()
    h, m, s = re.findall(r'time=(\d+):(\d+):([\d.]+)', out)[-1]
    return 3600 * int(h) + 60 * int(m) + float(s)


if __name__ == '__main__':
    voice = PiperVoice.load(SA, config_path=SA + '.json')
    if '--pace' in sys.argv:  # pratham at 0.7 / pali_sa at length 1: the length that evens them
        r = [seconds(pratham(t)) / seconds(pali_sa(voice, t, 1.0)) for t in TEXTS[5:]]
        print('length for pali_sa:', round(float(np.median(r)), 2), [round(x, 2) for x in r])
        sys.exit()
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        takes = [('pratham', pratham(text)), ('pali_sa', pali_sa(voice, text, SA_LENGTH))]
        random.Random(f'pisa1-{i}').shuffle(takes)
        vs = []
        for vid, (name, mp3) in zip('ab', takes):
            f = f'p{i:02d}.{vid}.mp3'
            open(f'{OUT}/{f}', 'wb').write(mp3)
            vs.append({'id': vid, 'label': vid.upper(), 'voice': name, 'file': f, 'sent': ''})
        phrases.append({'id': f'p{i:02d}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучше; ✓ правильно; ✗ неправильно. Тембр один, слушайте произношение'})
    json.dump({'round': 'pisa1', 'title': 'Пали: pratham или санскритский выговор с тембром pratham',
               'intro': 'Один тембр, два выговора: pratham с нашими правилами и pratham, доученный на санскритском чтении Parler. Вслепую, 0.7x. Оценивайте произношение; на слово с ошибкой можно нажать.',
               'sections': [{'id': 'p', 'title': 'Пали, 0.7x', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
