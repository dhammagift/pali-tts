"""Round miles1 (owner 2026-10-17: «присылай как раунд между тем что есть по англ яз и его голосом»): the Miles demo
voice (Piper from en_US-ryan on his first 100 record-en takes, Kaggle 2 h) against DG's English voices now, blind, on
6 Sujato lines from dg.db that are not in the record-en script; all through tts_server as DG reads English.
Usage (on f3): /root/venv-ml/bin/python round_miles1.py -> out/miles1/; then build_page.py with ROUND = 'miles1'
"""
import json
import os

from round_st1 import piper

OUT = 'out/miles1'
TEXTS = ['At one time the Buddha was staying near Rājagaha in the Bamboo Grove, the squirrels’ feeding ground.',
         'Then Venerable Upāli went up to the Buddha, bowed, sat down to one side, and said to him:',
         'We go for refuge to the Buddha, to the teaching, and to the mendicant Saṅgha.',
         'For someone who has attained the first absorption, sensual perceptions have ceased.',
         '‘It is not solely by mere faith that Āḷāra Kālāma declares: “I realize this teaching with my own insight, '
         'and live having achieved it.”',
         'Since I see no such reason, I live secure, fearless, and self-assured.']
VOICES = [('miles', 'Miles (демо, 100 строк)'), ('alan', 'alan ♂ UK (сейчас)'), ('norman', 'norman ♂ US (сейчас)'),
          ('kathleen', 'kathleen ♀ US (сейчас)')]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, label in VOICES:
            f = f'en{i}.{vid}.mp3'
            piper(text, vid, f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучший; ok — годится; ✗ — плохо. Слово с ошибкой — кликни по нему'})
    json.dump({'round': 'miles1', 'sections': [{'id': 'en', 'title': 'English: Miles и голоса DG, вслепую',
                                                'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
