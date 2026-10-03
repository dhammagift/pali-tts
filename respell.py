"""Pali words inside a translation, respelled so an English or Russian Piper voice says them sanely.

The en/ru voices phonemize with espeak, which reads IAST as English/Russian letters (Vārāṇasī,
Tathāgata -> "th" as in "think", phassa -> "f"). Russian: Pali in Latin -> Cyrillic by Pali sound.
English: diacritics off, aspirates folded into plain stops (an English voice can't aspirate on cue).
"""
import re
import unicodedata

PALI_CHARS = 'āīūṭḍṅñṇḷṃṁ'
# Pali without diacritics in an English sentence: doubled aspirates, ññ, or an aspirate opening the word
# (bhikkhu, dhamma, khandha). Not "ddh"/"tth": Buddha and Matthew read fine as English.
EN_PALI_HINT = re.compile(r'kkh|ggh|cch|jjh|ṭṭh|bbh|ññ|^(?:bh|dh|kh|gh|jh|ph)(?=[aeiou])')
WORD = re.compile(r"[A-Za-z" + PALI_CHARS + PALI_CHARS.upper() + r"ĀĪŪṬḌṄÑṆḶṂṀ]+")

RU = [  # longest first
    ('kh', 'кх'), ('gh', 'гх'), ('ch', 'чх'), ('jh', 'джх'), ('ṭh', 'тх'), ('ḍh', 'дх'), ('th', 'тх'),
    ('dh', 'дх'), ('ph', 'пх'), ('bh', 'бх'), ('ya', 'я'), ('yā', 'я'), ('yu', 'ю'), ('yū', 'ю'), ('ye', 'е'),
    ('a', 'а'), ('ā', 'а'), ('i', 'и'), ('ī', 'и'), ('u', 'у'), ('ū', 'у'), ('e', 'е'), ('o', 'о'),
    ('k', 'к'), ('g', 'г'), ('ṅ', 'н'), ('c', 'ч'), ('j', 'дж'), ('ñ', 'нь'), ('ṭ', 'т'), ('ḍ', 'д'),
    ('ṇ', 'н'), ('t', 'т'), ('d', 'д'), ('n', 'н'), ('p', 'п'), ('b', 'б'), ('m', 'м'), ('y', 'й'),
    ('r', 'р'), ('l', 'л'), ('ḷ', 'л'), ('v', 'в'), ('s', 'с'), ('h', 'х'), ('ṃ', 'м'), ('ṁ', 'м'),
    ('f', 'ф'), ('w', 'в'), ('z', 'з'), ('q', 'к'), ('x', 'кс'),
]
RU_RX = re.compile('|'.join(re.escape(k) for k, _ in sorted(RU, key=lambda kv: -len(kv[0]))))
RU_MAP = dict(RU)

EN = [('kh', 'k'), ('gh', 'g'), ('ch', 'ch'), ('jh', 'j'), ('ṭh', 't'), ('ḍh', 'd'), ('th', 't'), ('dh', 'd'),
      ('ph', 'p'), ('bh', 'b'), ('ā', 'aa'), ('ī', 'ee'), ('ū', 'oo'), ('c', 'ch'), ('ñ', 'ny'), ('ṅ', 'ng'),
      ('ṭ', 't'), ('ḍ', 'd'), ('ṇ', 'n'), ('ḷ', 'l'), ('ṃ', 'm'), ('ṁ', 'm')]
EN_RX = re.compile('|'.join(re.escape(k) for k, _ in sorted(EN, key=lambda kv: -len(kv[0]))))
EN_MAP = dict(EN)


def _case(src, out):
    return out[:1].upper() + out[1:] if src[:1].isupper() else out


def respell(text, lang):
    text = unicodedata.normalize('NFC', text)

    def word(m):
        w = m.group()
        low = w.lower()
        if lang == 'ru':
            return _case(w, RU_RX.sub(lambda x: RU_MAP[x.group()], low))  # any Latin word in Russian text
        if lang == 'en' and (any(c in PALI_CHARS for c in low) or EN_PALI_HINT.search(low)):
            return _case(w, EN_RX.sub(lambda x: EN_MAP[x.group()], low))
        return w
    return WORD.sub(word, text) if lang in ('ru', 'en') else text


if __name__ == '__main__':
    assert respell('Благословенный в Vārāṇasī, монахи (bhikkhū).', 'ru') == 'Благословенный в Варанаси, монахи (бхиккху).'
    assert respell('Tathāgata, phassa, Ñāṇa', 'ru') == 'Татхагата, пхасса, Ньана'
    assert respell('The Blessed One in Vārāṇasī dwells; the bhikkhus.', 'en') == 'The Blessed One in Vaaraanasee dwells; the bikkus.'
    assert respell('Tathāgata and phassa', 'en') == 'Tataagata and passa', respell('Tathāgata and phassa', 'en')
    assert respell('the thing that the Buddha said, abhorred', 'en') == 'the thing that the Buddha said, abhorred'  # English untouched
    assert respell('the Dhamma and dukkha', 'en') == 'the Damma and dukka'
    print('ok')
