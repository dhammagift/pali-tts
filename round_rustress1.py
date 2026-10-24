"""Round rustress1 (owner 2026-10-24: «генерируй проверки из сутт, проверим насколько работает такой метод»): how often is
RUAccent right where it and our Russian voice disagree (audit_ru_stress.py)? Words from the audit's top, each in a
real DG sentence; Puriso reads it as now and with RUAccent's stress (or ё) forced by a stress mark. Blind, the order
swapped per line. The answers give the method's hit rate before any of it becomes a rule.
Usage (on f3): .venv/bin/python round_rustress1.py -> out/rustress1/; then build_page.py with ROUND = 'rustress1'
"""
import base64
import json
import os
import random
import re
import sqlite3
import urllib.request

OUT = 'out/rustress1'
DB = '/var/www/dg-node-prod/dg.db'
# (word as printed, RUAccent's form): from the audit's top; Pali names left out (our names rule decides those)
WORDS = [('большая', 'бо́льшая'), ('прожита', 'прожита́'), ('моя', 'моя́'), ('принявшего', 'приня́вшего'),
         ('десятью', 'де́сятью'), ('памятующий', 'па́мятующий'), ('исчерпания', 'исче́рпания'), ('пятна', 'пятна́'),
         ('подпитываясь', 'подпи́тываясь'), ('тому', 'тому́'), ('перед', 'пе́ред'), ('уже', 'уже́'),
         ('черпает', 'черпа́ет'), ('стороны', 'стороны́'), ('зарождено', 'зарождено́'), ('душа', 'душа́'),
         ('вести', 'вести́'), ('дела', 'дела́'), ('ведание', 'ве́дание'), ('какая', 'ка́кая'), ('черта', 'чёрта'),
         ('зажженных', 'зажжённых'), ('милы', 'милы́'), ('сосредоточении', 'сосредото́чении'), ('берега', 'бе́рега'),
         ('образа', 'о́браза'), ('змея', 'змея́'), ('снято', 'снято́'), ('вещей', 'ве́щей'), ('развитые', 'ра́звитые'),
         ('слова', 'слова́'), ('дороги', 'до́роги')]
PREF = ('o', 'sv+edited+o', 'sv', 'syrkin+edited+o')


def sentence(db, word):
    rx = re.compile(rf'(?<![а-яё]){word}(?![а-яё])', re.I)
    for tr in PREF:
        rows = db.execute("select txt from texts where lang = 'ru' and translator = ? and lower(txt) like ?", (tr, f'%{word}%')).fetchall()
        good = sorted((t.strip() for (t,) in rows if rx.search(t) and 30 <= len(t.strip()) <= 170), key=len)
        if good:
            return good[len(good) // 2], rx
    return None, rx


def say(text):
    r = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': 'puriso', 'rate': 1.0}).encode(),
                               {'Content-Type': 'application/json'})
    return base64.b64decode(json.loads(urllib.request.urlopen(r, timeout=300).read())['audioContent'])


if __name__ == '__main__':
    db = sqlite3.connect(DB)
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, (word, theirs) in enumerate(WORDS):
        text, rx = sentence(db, word)
        if not text:
            print('no sentence for', word)
            continue
        fixed = rx.sub(lambda m: theirs[:1].upper() + theirs[1:] if m.group()[0].isupper() else theirs, text, count=1)
        takes = [('now', text), ('ruaccent', fixed)]
        random.Random(f'rs1-{i}').shuffle(takes)
        vs = []
        for vid, (name, t) in zip('ab', takes):
            f = f'w{i:02d}.{vid}.mp3'
            open(f'{OUT}/{f}', 'wb').write(say(t))
            vs.append({'id': vid, 'label': vid.upper(), 'voice': name, 'file': f, 'sent': ''})
        phrases.append({'id': f'w{i:02d}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'Слово «{word}»: где ударение правильное? ✓ правильно, ✗ неправильно (оба могут быть ✓)'})
    json.dump({'round': 'rustress1', 'sections': [{'id': 'w', 'title': 'Ударения: как сейчас или как предлагает RUAccent',
                                                   'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
