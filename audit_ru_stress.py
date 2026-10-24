"""Where our Russian voices stress a word differently from RUAccent (kaggle-ru-stress: word_stress.json, every word of
DG's Russian texts with its stressed forms in context and their counts). Owner 2026-10-24: find the errors before the
listeners do. Our stress: the stressed vowel of ru_phonemes (espeak + RU_STRESS/RU_ACCENT/ru_yo), as ru_stress_marks
reads it. Out: ru_stress_audit.tsv - count, word, ours, RUAccent's, its share among the word's forms, kind:
  stress - RUAccent puts it elsewhere, one reading (>= 90 % of the word's places): most likely our error;
  yo     - RUAccent reads ё where the text has е and we don't;
  homograph - RUAccent reads it two ways by context (за́мок / замо́к): a list for a person, not a rule.
Usage (on f3): .venv/bin/python audit_ru_stress.py word_stress.json
"""
import json
import re
import sys

from piper import PiperVoice

from respell import IPA_VOWELS, RU_ACCENT, RU_STRESS, RU_VOWELS, ru_phonemes

voice = PiperVoice.load('models/ru_puriso2-medium.onnx')
stats = json.load(open(sys.argv[1], encoding='utf-8'))


def ours(word):
    """Index (among the word's vowel letters) of the vowel our phonemes stress, or None where it can't be told."""
    ph = ''.join(p for s in ru_phonemes(voice, word) for p in s)
    ph = re.sub(f"ˈ([^{IPA_VOWELS}]*)", r"\1ˈ", ph)
    groups = re.findall(f"ˈ?[{IPA_VOWELS}]", ph)
    stressed = [k for k, g in enumerate(groups) if g.startswith('ˈ')]
    n = sum(c in RU_VOWELS for c in word)
    if len(stressed) != 1 or len(groups) != n:
        return None, 'ɵ' in ph
    return stressed[0], 'ɵ' in ph


def theirs(form):
    """RUAccent's form 'сл+ово' -> (index of the stressed vowel among the vowel letters, has ё)."""
    i = form.index('+')
    return sum(c in RU_VOWELS for c in form[:i]), 'ё' in form


def marked(word, k):
    idx = [i for i, c in enumerate(word) if c in RU_VOWELS]
    return word if k is None or k >= len(idx) else word[:idx[k] + 1] + '́' + word[idx[k] + 1:]


rows = []
for word, forms in stats.items():
    if sum(c in RU_VOWELS for c in word) < 2 or '-' in word or word in RU_ACCENT or word in RU_STRESS:
        continue  # our own rules (Pali names on the penult, the owner's fixes) are meant, RUAccent's guess is not
    total = sum(forms.values())
    top, n = max(forms.items(), key=lambda kv: kv[1])
    k_them, yo_them = theirs(top)
    k_us, yo_us = ours(word)
    them = top.replace('+', '').replace('ё', 'ё́') if yo_them else marked(top.replace('+', ''), k_them)
    readings = {theirs(f) for f in forms}
    if len(readings) > 1 and n / total < 0.9:
        kind = 'homograph'
    elif yo_them and not yo_us:
        kind = 'yo'
    elif k_us is not None and k_us != k_them:
        kind = 'stress'
    else:
        continue
    rows.append((total, word, marked(word, k_us), them, round(n / total, 2), kind))
rows.sort(reverse=True)
with open('ru_stress_audit.tsv', 'w', encoding='utf-8') as f:
    f.write('count\tword\tours\truaccent\tshare\tkind\n')
    for r in rows:
        f.write('\t'.join(map(str, r)) + '\n')
by = {}
for r in rows:
    by.setdefault(r[5], [0, 0])
    by[r[5]][0] += 1
    by[r[5]][1] += r[0]
print(len(stats), 'words;', {k: f'{w} words, {c} places' for k, (w, c) in by.items()})
