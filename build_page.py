"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'r23'
TITLE = 'Pali TTS — раунд 23: стабильность'
INTRO = ('Модель каждый раз подмешивает случайность, поэтому слог может пропасть в одном дубле из двух (jarāpi → «japi»). Здесь одни и те же фонемы (правила r20) при трёх уровнях случайности, по 3 дубля. Нужно понять, становится ли меньше пропусков. Вперемешку. '
         '<b>✓</b> все слоги на месте, <b>✗</b> что-то проглочено, <b>★</b> самый естественный.')
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
