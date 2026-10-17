"""Build site/index.html for a listening round from out/<ROUND>/index.json. Answers -> votes/<ROUND>.jsonl."""
import json
import random
import re
import time

ROUND = 'r54'
TITLE = 'Pali TTS — раунд 54: paggayha, asaṁvāso, sammutiyā, tikkhattuṁ'
INTRO = ('Остатки раундов 52–53: paggayha «пагейа» (открытое a, как помогло в dhārayāmīti), asaṁvāso, u в bhikkhusammutiyā, tikkhattuṁ без i и ṁ. 2 дубля, вперемешку, 0.7x.')
LANG = 'ru'  # 'en': the page's own words in English (owner: English rounds are for Miles, who has no Russian)
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
if LANG == 'en':
    for ru, en in [('<html lang="ru">', '<html lang="en">'), ('Pali TTS тест', 'DG voice test'),
                   ('Скорость всех плееров на странице', 'Speed of every player on the page'), ("'сохраняю…'", "'saving…'"),
                   ("'сохранено ✓' : 'ошибка сохранения'", "'saved ✓' : 'not saved (error)'"),
                   ("'нет сети — не сохранено'", "'offline — not saved'"), ('`Оценено: ${n} из ', '`Rated: ${n} of '),
                   ('`без оценок: ', '`unrated: '), ('нажмите на слово, которое лучший вариант читает неправильно',
                   'tap a word the best variant reads wrong'), ('Слушать / стоп', 'Play / stop'), ("'нравится' : 'лучший'", "'like' : 'best'"),
                   ('✓ норм', '✓ ok'), ('✗ плохо', '✗ bad'), ('Комментарий: что не так, как должно звучать…', 'Comment: what is wrong, how it should sound…'),
                   ('показать, кто есть кто', 'show who is who'), ('фонемы / письмо каннада', 'phonemes / script')]:
        assert ru in page, ru
        page = page.replace(ru, en)
page = page.replace('__TITLE__', TITLE).replace('__INTRO__', INTRO).replace('__DATA__', json.dumps({'round': ROUND, 'phrases': phrases}, ensure_ascii=False))
# one page per round (site/rNN.html) so an unanswered round is not replaced by the next one;
# site/index.html stays the latest
open(f'site/{ROUND}.html', 'w', encoding='utf-8').write(page)
open('site/index.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases), 'phrases')
