"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'r7'
TITLE = 'Pali TTS — раунд 7: конечное ṁ как .n для Piper pratham'
INTRO = ('Голос везде один — бесплатный офлайн Piper pratham. Правила раунда 4 уже применены (ñ → ɲj, ññ → ɲː, конечное ṁ → ŋː, темп прежний). ññ решён (ɲːj). Конечное ṁ по твоей подсказке как .n (ретрофлексное ɳ); n из раунда 6 — для сравнения. '
         'Варианты перемешаны. <b>★ лучший</b> (один на фразу), <b>✓ норм</b>, <b>✗ плохо</b>; <b>нажмите на слово</b>, которое лучший вариант читает неправильно.')
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
