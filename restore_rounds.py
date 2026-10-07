"""Rebuild the pages of rounds 1-19 (site/rN.html), overwritten in site/index.html at the time.
Each round with the builder + template of its own commit (the nearest later one if it had none), so the
saved answers (votes/rN.jsonl) load back. Round 1 predates the builder: its out/index.json is converted.
"""
import json
import os
import re
import subprocess
import sys

ROUNDS = range(1, 20)
LABELS = {'google': 'Google pa-IN (как сейчас)', 'rohan.ipa_stress': 'rohan · IPA + ударение', 'rohan.full_a': 'rohan · полное a',
          'rohan.full_a_stress': 'rohan · полное a + ударение', 'pratham.full_a_stress': 'pratham · полное a + ударение',
          'priyamvada.full_a_stress': 'priyamvada · полное a + ударение'}
# rounds whose builder was never committed: titles in the style of the others
TITLES = {1: 'первые голоса (Google, rohan, pratham, priyamvada)', 2: 'исправления произношения и выбор голоса',
          4: 'свои правила pratham: ñ, ññ, конечное ṁ, темп', 6: 'конечное ṁ для pratham', 8: 'конечное ṁ как ŋ без «г»',
          10: 'c звучит как «щ» (dhammacakka)'}


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, check=True).stdout


def builders():
    """round -> commit of build_page.py that built it, oldest first"""
    out = {}
    for c in reversed(git('log', '--format=%h', '--', 'build_page.py').split()):
        m = re.search(r"^ROUND = '(r\d+)'", git('show', f'{c}:build_page.py'), re.M)
        if m:
            out.setdefault(int(m.group(1)[1:]), c)
    return out


def round1():
    d = json.load(open('out/index.json', encoding='utf-8'))
    os.makedirs('out/r1', exist_ok=True)
    phrases = []
    for cid, c in d['cases'].items():
        vs = []
        for v in ['google'] + d['variants']:
            f = f'{cid}.{v}.mp3'
            if os.path.exists(f'out/{f}'):
                if not os.path.exists(f'out/r1/{f}'):
                    os.symlink(f'../{f}', f'out/r1/{f}')
                vs.append({'id': v, 'label': LABELS.get(v, v), 'file': f})
        phrases.append({'id': cid, 'text': c['text'], 'note': c['note'], 'ipa': c['ipa'], 'script': c.get('devanagari', ''), 'variants': vs})
    json.dump({'round': 'r1', 'sections': [{'id': 'p', 'title': 'Раунд 1', 'multi_best': False, 'phrases': phrases}]},
              open('out/r1/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def doc(n):
    p = f'round{n}.py'
    m = re.match(r'\s*"""(.*?)"""', open(p, encoding='utf-8').read(), re.S) if os.path.exists(p) else None
    return m.group(1).split('Usage')[0].strip().replace('\n', ' ') if m else ''


if __name__ == '__main__':
    b = builders()
    round1()
    for n in ROUNDS:
        c = b.get(n) or b[min(k for k in b if k > n)]
        src = git('show', f'{c}:build_page.py')
        tpl = git('show', f'{c}:page_template.html')
        open('_restore_template.html', 'w', encoding='utf-8').write(tpl)
        src = re.sub(r"^ROUND = '.*?'", f"ROUND = 'r{n}'", src, count=1, flags=re.M)
        if n not in b:
            src = re.sub(r"^TITLE = '.*?'", f"TITLE = 'Pali TTS — раунд {n}: {TITLES[n]}'", src, count=1, flags=re.M)
            src = re.sub(r"^INTRO = \(.*?\)\n", f"INTRO = {json.dumps(doc(n), ensure_ascii=False)}\n", src, count=1, flags=re.M | re.S)
        src = src.replace("'page_template.html'", "'_restore_template.html'")
        src = re.sub(r"open\(f?'site/[^']*'", f"open('site/r{n}.html'", src)
        exec(compile(src, f'build_page@{c}', 'exec'), {'__name__': '__main__'})
        assert os.path.exists(f'site/r{n}.html'), n
    os.remove('_restore_template.html')
