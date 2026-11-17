"""Where does our Russian reading (espeak + respell.ru_phonemes: the names list, RU_STRESS) put the stress, against a
stress-marked copy of the same lines (ruaccent: 'вр+емя')? Owner 2026-11-17: MN 129 full of wrong stress (дела,
одурманивающим) - word by word fixes do not scale. Prints the words that differ, most frequent first.
Usage: ru_stress_check.py plain.tsv accented.tsv   (id<TAB>text, the same lines in both)"""
import collections
import re
import sys

from piper import PiperVoice

from respell import RU_WORD, ru_phonemes

VOW = 'аеёиоуыэюя'
PH_VOW = set('aɑʌəeɛiɪyɨoɔuʊæɐ')


def espeak_stress(voice, text):
    """[(word, index of its stressed vowel or None)] in text order; None if espeak split the words differently."""
    words = RU_WORD.findall(text.lower())
    toks = [t for s in ru_phonemes(voice, text) for t in ''.join(s).split(' ') if any(c.isalpha() for c in t)]
    if len(toks) != len(words):
        return None
    out = []
    for w, t in zip(words, toks):
        k = t.find('ˈ')
        out.append((w, sum(c in PH_VOW for c in t[:k]) if k >= 0 else None))
    return out


def marked_stress(text):
    """ruaccent's '+' before the stressed vowel (ё is stressed by itself): [(word, index or None)]."""
    out = []
    for w in re.findall(r"[а-яё+-]+", text.lower()):
        w = w.strip('-')
        plain = w.replace('+', '')
        if not plain or not RU_WORD.fullmatch(plain):
            continue
        k = w.find('+')
        i = sum(c in VOW for c in w[:k]) if k >= 0 else (sum(c in VOW for c in plain[:plain.find('ё')]) if 'ё' in plain else None)
        out.append((plain, i))
    return out


if __name__ == '__main__':
    voice = PiperVoice.load('models/ru_owner_h3-medium.onnx')
    plain = dict(l.rstrip('\n').split('\t', 1) for l in open(sys.argv[1], encoding='utf-8') if '\t' in l)
    acc = dict(l.rstrip('\n').split('\t', 1) for l in open(sys.argv[2], encoding='utf-8') if '\t' in l)
    diff, words, lines = collections.Counter(), 0, 0
    for sid, text in plain.items():
        e, m = espeak_stress(voice, text), marked_stress(acc.get(sid, ''))
        if e is None or len(e) != len(m):
            continue
        lines += 1
        for (w, ei), (w2, mi) in zip(e, m):
            if w != w2 or sum(c in VOW for c in w) < 2 or mi is None:
                continue
            words += 1
            if ei != mi:
                s = ''.join(c + ('́' if c in VOW and sum(x in VOW for x in w[:j]) == mi else '') for j, c in enumerate(w))
                diff[(w, s)] += 1
    print(f'{lines} lines, {words} words of 2+ syllables compared, {sum(diff.values())} stressed differently '
          f'({len(diff)} distinct)')
    for (w, s), n in diff.most_common():
        print(f'{n}\t{w}\t{s}')
