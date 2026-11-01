"""Round 58 (owner 2026-11-01, Trello 06Cgj4G0: "Pali voice rattles", SN 35.245:8.1): after «rañño» five long words ran
4.5 s with no pause at all. Pauses between words, three ways, against the voice as it is: a comma after every word of a
comma-less run / a comma after long words only (4+ syllables) / long words read apart with 0.12 s of silence.
pratham through tts_server at the site's 0.7x (rate 0.875), blind. Usage (on f3): python3 round58.py -> out/r58/;
then build_page.py with ROUND = 'r58'
"""
import base64
import json
import os
import re
import subprocess
import urllib.request

OUT = 'out/r58'
API = 'http://127.0.0.1:3011/synthesize'
RATE = 0.875  # the site's default 0.7 (voice.js: uiRate / 0.8)
SR = 22050
GAP = 0.12
LINES = [('sn', 'Seyyathāpi, bhikkhu, rañño paccantimaṁ nagaraṁ daḷhuddhāpaṁ daḷhapākāratoraṇaṁ chadvāraṁ.'),
         ('mn10', 'Idha, bhikkhave, bhikkhu kāye kāyānupassī viharati ātāpī sampajāno satimā, vineyya loke abhijjhādomanassaṁ;'),
         ('dn2', 'Tattha cakkhumā puriso tīre ṭhito passeyya sippisambukampi sakkharakathalampi macchagumbampi carantampi tiṭṭhantampi.'),
         ('mn26', 'Puna caparaṁ, bhikkhave, bhikkhu sabbaso viññāṇañcāyatanaṁ samatikkamma ‘natthi kiñcī’ti ākiñcaññāyatanaṁ upasampajja viharati.')]
syllables = lambda w: len(re.findall(r'(?:ai|au|[aeiouāīū])', w.lower()))
long_word = lambda w: syllables(w) >= 4


def commas(text, every):
    """A comma after each word (every) or each long word that has no punctuation of its own; never after the last."""
    ws = text.split()
    return ' '.join(w + ',' if i < len(ws) - 1 and not re.search(r'[,.;:?!’]$', w) and (every or long_word(w)) else w
                    for i, w in enumerate(ws))


def pcm(text):
    req = urllib.request.Request(API, json.dumps({'text': text, 'rate': RATE, 'voice': 'pratham'}).encode(),
                                 {'Content-Type': 'application/json'})
    mp3 = base64.b64decode(json.load(urllib.request.urlopen(req))['audioContent'])
    return subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', '-', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-'],
                          input=mp3, capture_output=True, check=True).stdout


def apart(text):
    """Cut after each comma and each long word, every piece read on its own, GAP of silence between."""
    pieces, run = [], []
    for w in text.split():
        run.append(w)
        if re.search(r'[,;:]$', w) or long_word(w):
            pieces.append(' '.join(run))
            run = []
    if run:
        pieces.append(' '.join(run))
    gap = b'\0\0' * int(SR * GAP)
    trim = lambda b: b[:len(b.rstrip(b'\0')) + 1 & ~1]  # the piece's own trailing silence, whole samples
    return gap.join(trim(pcm(p)) for p in pieces)


def mp3(raw, path):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
                    '-q:a', '7', path], input=raw, check=True)


if __name__ == '__main__':
    assert commas('a bb, ccccccc dd.', True) == 'a, bb, ccccccc, dd.'
    assert commas('ākiñcaññāyatanaṁ upasampajja viharati.', False) == 'ākiñcaññāyatanaṁ, upasampajja, viharati.'
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for pid, text in LINES:
        vs = []
        for vid, label, raw in [('a', 'как сейчас', lambda: pcm(text)),
                                ('b', 'запятая после каждого слова', lambda: pcm(commas(text, True))),
                                ('c', 'запятая после длинных слов', lambda: pcm(commas(text, False))),
                                ('d', 'длинные слова отдельно, пауза 0.12 с', lambda: apart(text))]:
            f = f'{pid}.{vid}.mp3'
            mp3(raw(), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': ''})
        phrases.append({'id': pid, 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучше всех; ✓ норм; ✗ плохо (тараторит / рвано / неестественно)'})
    json.dump({'round': 'r58', 'title': 'Pali TTS — раунд 58: паузы между словами',
               'intro': 'Пали-голос тараторит, когда длинные слова идут подряд без запятых (SN 35.245:8.1). '
                        'Четыре варианта вслепую: как сейчас и три способа поставить паузы между словами. 0.7x, Pratham.',
               'sections': [{'id': 'p', 'title': 'паузы между словами, 0.7x', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
