"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'r3'
TITLE = 'Pali TTS — раунд 3: шлифуем Google'
INTRO = ('Голос везде один — Google pa-IN Achird, как сейчас в DG. Меняется только текст, который ему подаётся. '
         '<b>Google целиком:</b> текущий вариант; с исправленными na/ma; письмом гурмукхи (родное для панджаби: удвоения через ੱ); наш чистый деванагари. '
         '<b>Отдельные звуки:</b> короткие фразы, где меняется только одна вещь — конечное ṁ, ph или конечное e. '
         '<b>★ лучший</b> (один на фразу), <b>✓ норм</b>, <b>✗ плохо</b>; <b>нажмите на слово</b>, которое лучший вариант читает неправильно. Всё сохраняется само.')
idx = json.load(open(f'out/{ROUND}/index.json', encoding='utf-8'))
ver = int(time.time())
phrases = []
for sec in idx['sections']:
    for c in sec['phrases']:
        vs = list(c['variants'])
        if not sec['multi_best']:
            random.Random(ROUND + c['id']).shuffle(vs)  # blind: stable per round, different per phrase
        phrases.append({
            'id': c['id'], 'text': c['text'], 'note': c['note'], 'ipa': c['ipa'], 'script': c['script'],
            'section': sec['title'], 'multi': sec['multi_best'],
            'words': re.findall(r"[^\s—–]+", c['text']),
            'variants': [{'id': v['id'], 'letter': str(i + 1) if sec['multi_best'] else chr(65 + i), 'label': v['label'],
                          'src': f'audio/{ROUND}/{v["file"]}?v={ver}'} for i, v in enumerate(vs)],
        })

page = open('page_template.html', encoding='utf-8').read()
page = page.replace('__TITLE__', TITLE).replace('__INTRO__', INTRO).replace('__DATA__', json.dumps({'round': ROUND, 'phrases': phrases}, ensure_ascii=False))
open('site/index.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases), 'phrases')
