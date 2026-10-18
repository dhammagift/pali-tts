"""Round miles3 (owner 2026-10-18: «пусть он примет»): Miles hears his voice as DG has it now (fine-tuned from ryan, which
cuts the last sound of each line) against 30 minutes of training from joe on all 300 takes (line ends clean), on the
3 lines his miles2 note was about. Not blind: he decides whether the new one is right to go on with.
Usage (on f3): .venv/bin/python round_miles3.py [new model] -> out/miles3/; then build_page.py with ROUND = 'miles3', LANG = 'en'
"""
import json
import os
import sys

from piper import PiperVoice

from round_miles2 import read
from round_st1 import mp3

OUT = 'out/miles3'
NEW = sys.argv[1] if len(sys.argv) > 1 else '/root/en-miles/run5q/out/en_miles-medium.onnx'
TEXTS = ['And how, monks, is remembrance of breathing developed? How is it multiplied to be great-fruitful, to be great-beneficial?',
         'Having heard the sound of the local devas, the devas of the Four Great Kings proclaimed:',
         'vision-giving, knowledge-giving, that to equanimity, to knowing, to awakening, to Nibbana.']

if __name__ == '__main__':
    voices = [('now', 'Yojanāni now, in DG (endings cut)', PiperVoice.load('models/en_miles-medium.onnx')),
              ('new', 'New: 30 min of training on all 300 takes (endings fixed)', PiperVoice.load(NEW, config_path=NEW + '.json'))]
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, label, voice in voices:
            f = f'en{i}.{vid}.mp3'
            mp3(*read(voice, text), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': 'Listen to the end of each line. ★ best; ✓ ok; ✗ bad. Tap a word that is read wrong'})
    json.dump({'round': 'miles3', 'sections': [{'id': 'en', 'title': 'Yojanāni: are the line endings right now?',
                                                'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
