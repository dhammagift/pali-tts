"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'r32b'
TITLE = 'Pali TTS — раунд 32b: arahaṁ на 0.7x'
INTRO = ('Варианты, которые в r32 были «норм», в скорости 0.7x (в r32 было 1.0x, как на сайте), по 2 дубля, вперемешку. <b>★ лучший</b>, <b>✓ норм</b>, <b>✗ плохо</b>.')
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
