"""Build site/rec/index.html: every human recording of the owner, full-length players, keep/drop marks.

Metrics (SNR etc.) are added from out/survey/survey.json when present.
"""
import json
import os
import re
import urllib.request

TREE = 'https://api.github.com/repos/dhammagift/audio/git/trees/HEAD?recursive=1'
LOCAL = '/var/www/html/assets/audio/'
paths = sorted(x['path'] for x in json.load(urllib.request.urlopen(TREE))['tree'] if x['path'].endswith('.mp3'))
metrics = {m['path']: m for m in json.load(open('out/survey/survey.json'))} if os.path.exists('out/survey/survey.json') else {}

def group(p):
    n = os.path.basename(p)
    if '_jiv' in n: return 'Сутты, живое чтение (_jiv)'
    if p.startswith('dn/dn2.9/'): return 'DN 22 по разделам'
    if p.startswith(('bu-pm/', 'bi-pm/')):
        who = 'Бхиккху' if p.startswith('bu') else 'Бхиккхуни'
        if '-old' in n: return f'{who}-патимоккха: старые версии (-old)'
        if re.match(r'(Bu|Bi)-', n): return f'{who}-патимоккха: главы'
        return f'{who}-патимоккха: отдельные правила'
    return None

ORDER = ['Сутты, живое чтение (_jiv)', 'DN 22 по разделам', 'Бхиккху-патимоккха: главы', 'Бхиккхуни-патимоккха: главы',
         'Бхиккху-патимоккха: старые версии (-old)', 'Бхиккхуни-патимоккха: старые версии (-old)',
         'Бхиккху-патимоккха: отдельные правила', 'Бхиккхуни-патимоккха: отдельные правила']
items = [(group(p), p) for p in paths if group(p)]
items.sort(key=lambda x: (ORDER.index(x[0]), [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', x[1])]))
phrases = []
for g, p in items:
    src = ('/old/assets/audio/' + p) if os.path.exists(LOCAL + p) else 'https://raw.githubusercontent.com/dhammagift/audio/HEAD/' + p
    m = metrics.get(p)
    note = (f"{m['dur'] / 60:.1f} мин · шум {m['noise_db']} дБ · голос/шум {m['snr_db']} дБ" + (f" · клиппинг {m['clip_pct']}%" if m['clip_pct'] else '')) if m else ''
    phrases.append({'id': re.sub(r'[^A-Za-z0-9_.-]', '_', p)[:40], 'text': os.path.basename(p), 'note': note, 'ipa': '', 'script': '',
                    'section': g, 'multi': True, 'words': [],
                    'variants': [{'id': 'f', 'letter': '', 'label': p, 'src': src}]})
intro = (f'Все твои записи живым голосом — {len(phrases)} файлов, синтетика SC-Voice исключена. '
         '<b>✓ норм</b> — брать в обучение, <b>✗ плохо</b> — не брать, <b>★</b> — эталонное качество. '
         'Цифра «голос/шум» — чем больше, тем чище (SN 56.11 ≈ 33 дБ, плохой DN22-2a ≈ 22 дБ).')
page = open('page_template.html', encoding='utf-8').read()
page = page.replace('__TITLE__', 'Записи для обучения голоса').replace('__INTRO__', intro).replace(
    '__DATA__', json.dumps({'round': 'rec1', 'api': '../vote.php', 'phrases': phrases}, ensure_ascii=False))
os.makedirs('site/rec', exist_ok=True)
open('site/rec/index.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases), {g: sum(1 for x, _ in items if x == g) for g in ORDER})
