"""Listening page for open Russian voices (Kaggle job kaggle-ruvoices): every voice on the same lines,
names shown (a choice, not a blind test). -> site/ruvoices.html (site/audio is ../out)
Usage: python3 build_ruvoices.py
"""
import json
import re
import time

src = json.load(open('out/ruvoices/out/index.json', encoding='utf-8'))
ver = int(time.time())
phrases = []
for n, line in enumerate(src['lines']):
    phrases.append({
        'id': f'l{n}', 'text': line, 'note': 'имена голосов видны: ★ нравится (можно несколько), ✓ норм, ✗ плохо',
        'ipa': '', 'script': '', 'section': 'Открытые русские голоса', 'multi': True,
        'words': re.findall(r"[^\s—–]+", line),
        'variants': [{'id': f"{v['engine']}|{v['voice']}", 'letter': f"{v['engine']} · {v['voice']}",
                      'label': v['licence'], 'src': f"audio/ruvoices/out/{v['files'][n]}?v={ver}"}
                     for v in src['voices'] if len(v['files']) > n],
    })
page = open('page_template.html', encoding='utf-8').read()
page = (page.replace('__TITLE__', 'Открытые русские голоса: сравнение')
        .replace('__INTRO__', 'Одни и те же фразы (SN 56.11 в твоём переводе и демо-фразы плеера) разными открытыми голосами, которые работают без видеокарты. Отметь, какие нравятся: из них выберем голос для перевода или основу под твой тембр.')
        .replace('__DATA__', json.dumps({'round': 'ruvoices', 'phrases': phrases}, ensure_ascii=False)))
open('site/ruvoices.html', 'w', encoding='utf-8').write(page)
print('ok', len(src['voices']), 'voices')
