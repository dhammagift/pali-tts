"""Round miles8 (owner 2026-10-26: show Miles that short words and lines are fixed): Yojanāni ~97 epochs (now in DG:
miles2 + the short ElevenLabs lines, kaggle-yojanani-long) against the voice DG had until today (28 epochs on miles2,
a word alone read after "the word" and cut). Both through tts_server's own synth_pcm, at the same gain. Blind, for Miles.
Usage (on f3): .venv/bin/python round_miles8.py -> out/miles8/; then build_page.py with ROUND = 'miles8', LANG = 'en'
"""
import json
import os

from round_miles4 import TEXTS as TEXTS4
from round_st1 import mp3

src = open('tts_server.py', encoding='utf-8').read()
exec(src[:src.index('\nprune_cache(')])  # the server's functions without starting it
OLD = '/root/claudeBak/miles-v2-28ep/en_miles-medium'  # the 28-epoch model with its json ("lead") and align model
VOICES['old'] = (os.path.relpath(OLD, MODELS), 'en', 'old')
GAIN['old'] = GAIN['miles']
OUT = 'out/miles8'
SHORT = ['Monks.', 'Mendicants!', 'What five?', 'Body.', 'Good.', 'Thus.', 'Feeling.', 'Chapter One.', 'mind', 'river']
TEXTS = SHORT + TEXTS4[-4:]

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, name in zip('ab', ('old', 'miles') if i % 2 == 0 else ('miles', 'old')):  # blind: A is not always the old
            f = f'en{i}.{vid}.mp3'
            mp3(*synth_pcm(text, name, 1.0), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': vid.upper(), 'voice': 'now' if name == 'miles' else 'old', 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ best; ✓ ok; ✗ bad. Is the word clear? Tap a word that is read wrong'})
    json.dump({'round': 'miles8', 'title': 'Yojanāni: short words and lines',
               'intro': 'Two versions of your voice, blind (A and B swap). The first lines are single words and short '
                        'lines, which the voice used to misread; then a few ordinary sentences. Mark each take.',
               'sections': [{'id': 'en', 'title': 'Yojanāni: which is clearer?', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
