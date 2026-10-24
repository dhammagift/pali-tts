"""Round rustress2 (owner 2026-10-24: «без отвеченных пришли»): the lines of rustress1 not answered yet, in the new answer
form - tap the word, then the syllable the stress belongs on (green); red «другое» for any other misreading. Same audio.
Usage (on main): python3 round_rustress2.py -> out/rustress2/; then build_page.py with ROUND = 'rustress2'
"""
import json
import os
import shutil

SRC, OUT = 'out/rustress1', 'out/rustress2'
answered = {json.loads(line)['phrase'] for line in open('votes/rustress1.jsonl', encoding='utf-8')
            if json.loads(line)['kind'] in ('rating', 'words', 'comment')}
idx = json.load(open(f'{SRC}/index.json', encoding='utf-8'))
os.makedirs(OUT, exist_ok=True)
phrases = [p for p in idx['sections'][0]['phrases'] if p['id'] not in answered]
for p in phrases:
    for v in p['variants']:
        shutil.copy(f'{SRC}/{v["file"]}', f'{OUT}/{v["file"]}')
    p['note'] = p['note'].split(':')[0]
json.dump({'round': 'rustress2', 'title': 'Ударения: где оно должно быть',
           'intro': 'Нажмите на слово, где ударение не на месте, и выберите слог, где оно должно быть: он станет зелёным. «другое» (красный) — слово прочитано неверно не из-за ударения. A и B — как читает голос сейчас и как предлагает RUAccent, их можно не оценивать.',
           'sections': [{'id': 'w', 'title': 'Ударения: где оно должно быть?', 'multi_best': False,
                                               'stress': True, 'phrases': phrases}]},
          open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', len(phrases))
