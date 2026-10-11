"""stress_names.tsv: Pali names in the SuttaCentral translations, stressed on the penult (owner 2026-10-11: СарипУтта,
МоггаллАна, РаджагАха, МантаниПУтта, as earlier ВаранАси, ИсипатАна; espeak guessed СарИпутта, РаджАгаха).
ru: every form of a name found in the Russian translations, with U+0301 on its stressed vowel (espeak ru reads the mark).
en: the forms espeak stresses elsewhere (a word with diacritics is Pali, a plain one must match a Pali form); respell.en_parts gives them our phonemes with the penult stress.
A name = its stem matches a capitalised word of the Pali root texts. Russian words (hunspell ru_RU knows them) stay out.
Usage: .venv/bin/python make_stress_names.py (needs sc-data, hunspell, the Piper en voice); review the diff, commit.
"""
import collections
import glob
import json
import re
import subprocess
import unicodedata

from piper import PiperVoice

import respell
from pali_ipa import to_ipa

SC = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data'
RU_VOW = 'аеиоуыэюяё'
NUCLEUS = re.compile(r'[əaɪiʊueoʌ]ː?')  # our Pali IPA, unstressed
EN_NUCLEUS = re.compile(r'[ɑɐəɪiʊuɛeæʌɒɔoɜaɚ]+[ːʊɪə]*')  # an English vowel with its glide or length
EXTRA = [('ru', 'бе́лок'),  # «место кормления белок»: squirrels, not protein
         ('en', 'mantāniputta')]  # owner's list; SC writes Mantāṇiputta


def ru_stem(w):
    return re.sub(r'(ой|ою|ей|ею|ами|ам|ах|ом|ов|[аеиоуыюяй])$', '', w)


def texts(lang):
    for f in glob.glob(f'{SC}/translation/{lang}/**/*.json', recursive=True):
        yield from (t for t in json.load(open(f, encoding='utf-8')).values() if isinstance(t, str))


def caps(text, rx):  # capitalised words, not glued to a hyphen (parts of compounds)
    return [m.group() for m in re.finditer(rx, unicodedata.normalize('NFC', text))
            if text[m.start() - 1:m.start()] != '-' and text[m.end():m.end() + 1] != '-']


def russian(words):
    unknown = subprocess.run(['hunspell', '-d', '/usr/share/hunspell/ru_RU', '-l'], input='\n'.join(words),
                             capture_output=True, text=True).stdout.split()
    return set(words) - set(unknown)


def ru_accent(w):
    pos = [m.start() for m in re.finditer(f'[{RU_VOW}]', w)]
    i = pos[len(re.findall(f'[{RU_VOW}]', ru_stem(w))) - 1]
    return w[:i + 1] + '́' + w[i + 1:]


if __name__ == '__main__':
    pali = collections.Counter(w for f in glob.glob(f'{SC}/root/pli/ms/**/*.json', recursive=True)
                               for t in json.load(open(f, encoding='utf-8')).values()
                               for w in caps(t, r'\b[A-ZĀĪŪÑṬḌṄṆḶ][a-zāīūṭḍṅñṇḷṃṁ]+'))
    pstems = {ru_stem(respell.respell(w, 'ru').lower()) for w in pali}
    ru = collections.Counter(w.lower() for t in texts('ru') for w in caps(t, r'\b[А-ЯЁ][а-яё]+'))
    ru = {w for w in ru if len(ru_stem(w)) >= 3 and ru_stem(w) in pstems and len(re.findall(f'[{RU_VOW}]', w)) >= 2}
    ru -= russian(sorted(ru))
    rows = [('ru', ru_accent(w)) for w in sorted(ru)]

    plain = {unicodedata.normalize('NFD', w.lower()).encode('ascii', 'ignore').decode(): w.lower() for w in pali}
    en = collections.Counter(w.lower() for t in texts('en') for w in caps(t, r'\b[A-ZĀĪŪÑṬḌṄṆḶ][A-Za-z' + respell.PALI_CHARS + ']+'))
    english = {w for t in texts('en') for w in re.findall(r'\b[a-z]+\b', t)}  # done, line, gate: also Pali vocatives
    en = {w for w in en if w not in english}
    voice = PiperVoice.load('models/en_GB-alan-medium.onnx')
    respell.EN_PENULT.clear()  # espeak's own stress, not the last run's fix
    for w in sorted(en):
        if w.endswith('s') and w[:-1] in en:
            continue  # bhikkhunīs: read as its singular plus -z
        pw = w if any(c in respell.PALI_CHARS for c in w) or w.capitalize() in pali else plain.get(w)  # Anāthapiṇḍika: no such Pali form
        if not pw:
            continue
        n = len(NUCLEUS.findall(to_ipa(pw, stress=False, final_m=True)))
        ph = ''.join(respell.en_phonemes(voice, w)).split('ˈ')
        if n >= 2 and len(ph) == 2 and (len(EN_NUCLEUS.findall(ph[0])) != n - 2 or len(EN_NUCLEUS.findall(''.join(ph))) != n):
            rows.append(('en', w))
    rows += EXTRA
    with open('stress_names.tsv', 'w', encoding='utf-8') as f:
        f.write(''.join(f'{lang}\t{w}\n' for lang, w in sorted(set(rows))))
    print(collections.Counter(lang for lang, _ in rows))
