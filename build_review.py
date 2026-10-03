"""Build site/review/index.html: listen to dataset clips (raw vs denoised) and mark bad ones.

Usage: python build_review.py <unzipped review artifact dir> [round] [clips per file]
A file whose median alignment score is low most likely has the wrong text range: it is flagged in its heading.
"""
import json
import os
import random
import re
import shutil
import statistics
import sys
import time

src = sys.argv[1]
ROUND = sys.argv[2] if len(sys.argv) > 2 else 'ds1'
PER_FILE = int(sys.argv[3]) if len(sys.argv) > 3 else 0  # 0 = all clips
dst = 'site/review'
shutil.rmtree(f'{dst}/clips', ignore_errors=True)
shutil.copytree(f'{src}/review', f'{dst}/clips')
clips = json.load(open(f'{src}/clips.json', encoding='utf-8'))
ver = int(time.time())
med = {it: statistics.median(c['score'] for c in clips if c['item'] == it) for it in {c['item'] for c in clips}}
if PER_FILE:
    clips = [c for it in med for c in random.Random(it).sample([c for c in clips if c['item'] == it],
             min(PER_FILE, sum(c['item'] == it for c in clips)))]
    clips.sort(key=lambda c: (c['item'], c['n']))
phrases = [{
    'id': c['name'].replace('.', '_'), 'text': c['text'], 'ipa': c['ipa'], 'script': ', '.join(c['keys']),
    'note': f"{c['item']} · {c['dur']} с · совпадение с текстом {c['score']:.2f} (мин. слово {c['min_score']:.2f})",
    'section': f"{c['item']} · медиана совпадения {med[c['item']]:.2f}" + (' ⚠ похоже, не тот текст' if med[c['item']] < 0.6 else ''), 'multi': True, 'words': re.findall(r'\S+', c['text']),
    'variants': [{'id': kind, 'letter': '', 'label': label, 'src': f'clips/{c["item"]}/{c["n"]:03d}.{kind}.mp3?v={ver}'}
                 for kind, label in (('raw', 'исходник'), ('dn', 'после шумоподавления'))],
} for c in clips]
mins = sum(c['dur'] for c in clips) / 60
intro = (f'Тестовая нарезка твоих записей: {len(clips)} клипов, {mins:.1f} мин. Текст под каждым клипом — что, по мнению выравнивания, там звучит. '
         '<b>✓ норм</b> — текст совпадает и звук годится; <b>✗ плохо</b> — не тот текст, обрезано, шум; '
         '<b>★</b> — эта версия (исходник или шумодав) лучше. Нажмите на слово, если его нет в записи или оно обрезано. '
         'Число «совпадение» — уверенность выравнивания (1.0 — идеально); по нему потом отсеем плохое автоматически.')
page = open('page_template.html', encoding='utf-8').read()
page = page.replace('__TITLE__', 'Проверка нарезки для обучения голоса').replace('__INTRO__', intro).replace(
    '__DATA__', json.dumps({'round': ROUND, 'api': '../vote.php', 'phrases': phrases}, ensure_ascii=False))
os.makedirs(dst, exist_ok=True)
open(f'{dst}/index.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases), 'clips', round(mins, 1), 'min')
