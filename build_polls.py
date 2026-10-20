"""The polls page (owner 2026-10-20: «собери тесты и опросы на какую-то страницу, а то теряется в чате»): every listening
round, newest first, with how much of it is answered (votes/<round>.jsonl), and the questions that are not rounds
(polls.json "questions", edited by hand; "done": true moves one down). A round answered outside the page or
superseded goes in polls.json "closed"; one older than a week with no answer is archived too. Run on main, where the votes land (cron, every 10 min).
Usage: python3 build_polls.py -> site/polls.html
"""
import glob
import html
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WHO = {'owner': 'вам', 'miles': 'Miles'}


def rounds():
    out = []
    for page in glob.glob(f'{HERE}/site/*.html'):
        rid = os.path.basename(page)[:-5]
        idx = f'{HERE}/out/{rid}/index.json'
        if rid == 'polls' or not os.path.exists(idx):
            continue
        src = open(page, encoding='utf-8').read()
        title = html.unescape(re.search(r'<h1>(.*?)</h1>', src).group(1))
        data = json.load(open(idx, encoding='utf-8'))
        phrases = {p['id'] for s in data.get('sections', [data]) for p in s['phrases']}
        votes = f'{HERE}/votes/{rid}.jsonl'
        rated = {json.loads(l)['phrase'] for l in open(votes, encoding='utf-8')} & phrases if os.path.exists(votes) else set()
        out.append({'id': rid, 'title': title, 'n': len(phrases), 'rated': len(rated), 'when': os.path.getmtime(page),
                    'who': 'miles' if '<html lang="en"' in src else 'owner'})
    return sorted(out, key=lambda r: -r['when'])


def item(q):
    parts = [f'<h3>{html.escape(q["title"])} <span class="who">· {WHO.get(q.get("who"), "")}</span></h3>',
             f'<p>{html.escape(q["text"])}</p>']
    for line in q.get('lines', []):
        parts.append(f'<div class="line"><code>{html.escape(line)}</code><button onclick="copy(this)">копировать</button></div>')
    for f in q.get('audio', []):
        parts.append(f'<div class="aud"><span>{html.escape(os.path.basename(f)[:-4])}</span><audio controls preload="none" src="audio/{html.escape(f)}"></audio></div>')
    if q.get('links'):
        parts.append('<p>' + ' · '.join(f'<a href="{html.escape(u)}">{html.escape(t)}</a>' for t, u in q['links']) + '</p>')
    return '<section>' + ''.join(parts) + '</section>'


def row(r):
    state = 'done' if r['rated'] >= r['n'] else 'part' if r['rated'] else 'new'
    day = time.strftime('%d.%m', time.localtime(r['when']))
    return (f'<a class="row {state}" href="{r["id"]}.html"><span class="t">{html.escape(r["title"])}</span>'
            f'<span class="m">{day} · {r["rated"]}/{r["n"]}{" · Miles" if r["who"] == "miles" else ""}</span></a>')


def page():
    cfg = json.load(open(f'{HERE}/polls.json', encoding='utf-8'))
    qs, rs = cfg['questions'], rounds()
    open_ = lambda r: r['rated'] < r['n'] and r['id'] not in cfg['closed'] and time.time() - r['when'] < 7 * 86400
    wait = [r for r in rs if open_(r)]
    done = [r for r in rs if not open_(r)]
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Голос DG: опросы</title>
<style>
:root{{--bg:#faf8f4;--fg:#222;--muted:#6b6560;--card:#fff;--line:#e6e0d8;--accent:#b5651d;--good:#2e7d32;--part:#b8860b;--new:#c62828}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16140f;--fg:#ece6dc;--muted:#a59d92;--card:#211e18;--line:#3a352c;--accent:#e0a060;--good:#66bb6a;--part:#f0c040;--new:#ef5350}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,sans-serif}}
main{{max-width:820px;margin:auto;padding:16px 16px 60px}}h1{{font-size:1.35rem;margin:.2em 0}}h2{{font-size:1.1rem;margin:1.4em 0 .4em}}
h3{{font-size:1rem;margin:0 0 .3em}}.who{{color:var(--muted);font-weight:400}}.lead{{color:var(--muted);font-size:.92rem}}
section{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0}}section p{{margin:.3em 0}}
.line{{display:flex;gap:8px;align-items:center;margin:6px 0}}.line code{{flex:1;font-size:.9rem;background:var(--bg);padding:6px 8px;border-radius:8px;overflow-wrap:anywhere}}
button{{font:inherit;font-size:.82rem;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:8px;padding:5px 9px;cursor:pointer}}
.aud{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0;font-size:.85rem;color:var(--muted)}}.aud audio{{width:100%;max-width:420px}}
a{{color:var(--accent)}}.row{{display:flex;justify-content:space-between;gap:10px;padding:9px 12px;border:1px solid var(--line);border-left:4px solid var(--line);
border-radius:10px;margin:6px 0;background:var(--card);color:var(--fg);text-decoration:none}}.row .m{{color:var(--muted);font-size:.85rem;white-space:nowrap}}
.row.new{{border-left-color:var(--new)}}.row.part{{border-left-color:var(--part)}}.row.done{{border-left-color:var(--good)}}
details summary{{cursor:pointer;color:var(--muted);margin:1.2em 0 .4em}}
</style></head><body><main>
<h1>Голос DG: опросы и тесты</h1>
<p class="lead">Всё, что ждёт ответа, в одном месте. Обновляется само каждые 10 минут; {time.strftime('%d.%m %H:%M')}.</p>
<h2>Вопросы</h2>
{''.join(item(q) for q in qs if not q.get('done')) or '<p class="lead">Нет открытых вопросов.</p>'}
<h2>Раунды без ответа ({len(wait)})</h2>
{''.join(row(r) for r in wait) or '<p class="lead">Все раунды отвечены.</p>'}
<details><summary>Отвеченные и старые раунды ({len(done)})</summary>{''.join(row(r) for r in done)}</details>
{''.join(item(q) for q in qs if q.get('done'))}
</main>
<script>function copy(b){{navigator.clipboard.writeText(b.previousElementSibling.textContent).then(()=>{{b.textContent='скопировано';setTimeout(()=>b.textContent='копировать',1500)}})}}</script>
</body></html>
'''


if __name__ == '__main__':
    tmp = f'{HERE}/site/polls.html.tmp'
    open(tmp, 'w', encoding='utf-8').write(page())
    os.replace(tmp, f'{HERE}/site/polls.html')
    print('ok')
