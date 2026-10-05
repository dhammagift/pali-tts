"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'es2'
TITLE = 'espeak-ng: пали, второй проход'
INTRO = ('Поправки по твоим заметкам к es1 — <b>в самом звуке espeak</b>: запятая без подъёма тона (me, sā, bho), ударение почти не тянет гласную (udānesi, abhisambuddho, dve), r всегда одним ударом, j как «дж», v без «м». '
         'Фонемы (то, что берёт Piper) не менялись. Где в es1 была жалоба — рядом «как было». Дальше pratham и твой голос по тем же фонемам. <b>✓</b> правильно, <b>✗</b> ошибка; <b>нажмите на слово</b>, если неправильно.')
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
