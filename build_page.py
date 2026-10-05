"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'r30'
TITLE = 'Pali TTS — раунд 30: окончание хинди в наших словах'
INTRO = ('В r29 победила анусвара хинди (ं): после a — «ən», после u — носовая «ũ». Здесь это окончание поставлено в наши слова (остальное слово — наши фонемы, без хиндийского проглатывания). '
         'Рядом — сам хинди-вариант из r29, где он есть. Названия видны. <b>★</b> где ṁ звучит правильно (можно несколько), <b>✓ норм</b>, <b>✗ плохо</b>.')
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
# one page per round (site/rNN.html) so an unanswered round is not replaced by the next one;
# site/index.html stays the latest
open(f'site/{ROUND}.html', 'w', encoding='utf-8').write(page)
open('site/index.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases), 'phrases')
