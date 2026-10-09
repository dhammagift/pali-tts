"""Supertonic 3 (supertone-oss-archive/supertonic, 99M, ONNX, archived 2026-09) for English and Russian: how it reads
Pali names and places inside a translation. Against the voice DG has now for that language (Piper alan / ruslan,
through the local tts_server). 5 phrases per language, 1 take each, blind.
Setup (f3): git clone the repo to /var/www/supertonic, `hf download supertone-oss-archive/supertonic-3
--revision aafc6e32416a594460b32413efc49d7fe4ce6d46 --local-dir assets` there; onnxruntime + soundfile in .venv-ears.
Usage (on f3): .venv-ears/bin/python round_st1.py -> out/st1/; then build_page.py with ROUND = 'st1'
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np

ST = '/var/www/supertonic'
sys.path.insert(0, f'{ST}/py')
from helper import load_text_to_speech, load_voice_style  # noqa: E402

OUT = 'out/st1'
TEXTS = {
    'en': ['So I have heard. At one time the Buddha was staying near Sāvatthī in Jeta’s Grove, Anāthapiṇḍika’s monastery.',
           'At one time the Buddha was staying in the land of the Kurus, near the Kuru town named Kammāsadamma.',
           'Then Venerable Sāriputta and Venerable Mahāmoggallāna went to the Vulture’s Peak near Rājagaha.',
           'At one time the Buddha was staying near Varanasi, in the deer park at Isipatana.',
           'King Pasenadi of Kosala went to see Queen Mallikā, and Ānanda told the Buddha at Vesālī, in the Great Wood.'],
    'ru': ['Так я слышал. Однажды Благословенный пребывал в Саваттхи, в роще Джеты, в монастыре Анатхапиндики.',
           'Однажды Благословенный пребывал в стране Куру, в городе куру под названием Каммасадхамма.',
           'Тогда Достопочтенный Сарипутта и Достопочтенный Махамоггаллана отправились на Пик Стервятников близ Раджагахи.',
           'Однажды Благословенный пребывал в Варанаси, в Оленьем парке в Исипатане.',
           'Царь Косалы Пасенади пришёл к царице Маллике, а Ананда рассказал об этом Благословенному в Весали, в Великом лесу.'],
}
NOW = {'en': 'alan', 'ru': 'ruslan'}  # the DG voice for that language today


def mp3(audio, sr, f):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-q:a', '5', f], input=audio.astype(np.float32).tobytes(), check=True)


def piper(text, voice, f):
    req = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': voice}).encode(),
                                 {'Content-Type': 'application/json'})
    raw = base64.b64decode(json.loads(urllib.request.urlopen(req, timeout=120).read())['audioContent'])
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-af', 'loudnorm=I=-18:TP=-1.5', '-q:a', '5', f],
                   input=raw, check=True)


if __name__ == '__main__':
    tts = load_text_to_speech(f'{ST}/assets/onnx')
    styles = {v: load_voice_style([f'{ST}/assets/voice_styles/{v}.json']) for v in ('M1', 'F1')}
    os.makedirs(OUT, exist_ok=True)
    sections = []
    for lang, texts in TEXTS.items():
        phrases = []
        for i, text in enumerate(texts):
            vs = []
            for vid, v in (('a', 'M1'), ('b', 'F1')):
                f = f'{lang}{i}.{vid}.mp3'
                wav, dur = tts(text, lang, styles[v], 8, 1.05)
                mp3(wav.reshape(-1)[:int(tts.sample_rate * dur[0])], tts.sample_rate, f'{OUT}/{f}')
                vs.append({'id': vid, 'label': f'Supertonic 3 · {v}', 'file': f, 'sent': text})
            f = f'{lang}{i}.c.mp3'
            piper(text, NOW[lang], f'{OUT}/{f}')
            vs.append({'id': 'c', 'label': f'сейчас в DG · Piper {NOW[lang]}', 'file': f, 'sent': text})
            phrases.append({'id': f'{lang}{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                            'note': '★ где имена и места звучат правильно и речь естественная'})
        sections.append({'id': lang, 'title': {'en': 'English', 'ru': 'Русский'}[lang] + ': имена и места пали',
                         'multi_best': False, 'phrases': phrases})
    json.dump({'round': 'st1', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for s in sections for p in s['phrases']))
