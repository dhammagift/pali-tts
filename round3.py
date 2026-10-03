"""Round 3: polish the Google pa-IN pipeline that DG uses (user's best so far).

Whole phrases: current vs na/ma bug fixed vs Gurmukhi vs our clean Devanagari.
Micro tests: same Google voice, only the spelling of one feature changes (final ṁ, ph, final e).
Usage: .venv/bin/python round3.py  -> out/r3/*.mp3, out/r3/index.json
"""
import base64
import json
import os
import re
import shutil
import urllib.request

from pali_ipa import to_script

OUT = 'out/r3'
VOICE = 'pa-IN-Chirp3-HD-Achird'
KEY = json.load(open('/var/www/dg-node-test/configs/local/tts-config.json'))['key']
cases = {l.split('\t')[0]: l.rstrip('\n').split('\t')[1:] for l in list(open('cases.tsv', encoding='utf-8'))[1:]}
dev = json.load(open('out/devanagari.json', encoding='utf-8'))
END = r'(?=[\s.,;:?!।]|$)'
NASALS = 'ङञणनम'
ASP = {'क': 'ख', 'ग': 'घ', 'च': 'छ', 'ज': 'झ', 'ट': 'ठ', 'ड': 'ढ', 'त': 'थ', 'द': 'ध', 'प': 'फ', 'ब': 'भ'}


def gurmukhi(deva):
    """Devanagari -> Gurmukhi the Punjabi way: addak for geminates, tippi for nasal+consonant."""
    s = deva.replace('‌', '')
    s = re.sub(r'([क-ह])्([क-ह])', lambda m: 'ੱ' + m[2] if m[2] in (m[1], ASP.get(m[1])) else m[0], s)
    s = re.sub(rf'([{NASALS}])्(?=[क-ह])', 'ं', s)
    return ''.join(chr(ord(c) + 0x100) if 0x900 <= ord(c) <= 0x963 else c for c in s).replace('ਂ', 'ੰ')


def google(path, text):
    if os.path.exists(path):
        return
    body = json.dumps({'input': {'text': text}, 'voice': {'languageCode': VOICE[:5], 'name': VOICE},
                       'audioConfig': {'audioEncoding': 'MP3'}}).encode()
    req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize?key=' + KEY, body,
                                 {'content-type': 'application/json', 'Referer': 'https://dhamma.gift/'})
    open(path, 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=30))['audioContent']))


def phrase(cid, variants, note=None):
    text, n = cases[cid]
    vs = []
    for vid, label, t in variants:
        f = f'{OUT}/{cid}.{vid}.mp3'
        if t is None:
            shutil.copy(f'out/{cid}.google.mp3', f)
            t = dev[cid]['google']
        else:
            google(f, t)
        vs.append({'id': vid, 'label': label, 'file': os.path.basename(f), 'sent': t})
    print(cid)
    return {'id': cid, 'text': text, 'note': note or n, 'ipa': '', 'script': '', 'variants': vs}


os.makedirs(OUT, exist_ok=True)
whole = []
for cid in ['c9', 'c14', 'c1', 'c4', 'c10', 'c11']:
    fixed = dev[cid]['fixed']
    clean = re.sub('म्' + END, 'ङ्', to_script(cases[cid][0], 'deva'))
    whole.append(phrase(cid, [
        ('google', 'Сейчас в DG', None),
        ('fixed', 'Исправлен баг na/ma (тянулись все na/ma)', fixed),
        ('guru', 'Исправленный + письмо гурмукхи', gurmukhi(fixed)),
        ('clean', 'Наш чистый деванагари без «удлинений»', clean),
    ]))

m1 = dev['m1']['fixed']
m2 = dev['m2']['fixed']
m3 = dev['m3']['fixed']
micro = [
    phrase('m1', [(v, f'конечное ṁ как {s}', re.sub('ङ्' + END, s, m1)) for v, s in
                  [('ng', 'ङ्'), ('ngg', 'ङ्ग्'), ('anus', 'ं'), ('m', 'म्'), ('nga', 'ङ')]],
           'Только конечное ṁ пишется по-разному. ★ — где слышно правильное «-ṁ»'),
    phrase('m2', [(v, f'ph как {s}', m2.replace('प्ह', s)) for v, s in
                  [('p_h', 'प्ह'), ('pha', 'फ'), ('zwnj', 'प्‌ह'), ('paha', 'पह')]] +
           [('guru', 'ph как ਫ (гурмукхи)', gurmukhi(m2.replace('प्ह', 'फ')))],
           'Только ph пишется по-разному. ★ — где «пх», а не «ф» и не «паха»'),
    phrase('m3', [('e', 'конечное e как े', m3),
                  ('e_ind', 'конечное e отдельной буквой ए', re.sub('([क-ह])े' + END, r'\1्ए', m3).replace('य्ए', 'यए')),
                  ('guru', 'гурмукхи', gurmukhi(m3))],
           'sattanikāye, jetavane, ārāme: слышно ли конечное «-е» и «дж» в jetavane'),
]
json.dump({'round': 'r3', 'sections': [
    {'id': 'whole', 'title': 'Google целиком', 'multi_best': False, 'phrases': whole},
    {'id': 'micro', 'title': 'Отдельные звуки', 'multi_best': False, 'phrases': micro},
]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
