"""'Ears': compare what a voice was asked to say (our IPA) with what a phoneme recogniser heard
(wav2vec2-lv-60-espeak-cv-ft, Kaggle job pali-tts-ears -> out/ears/heard.json).
Both sides are reduced to broad classes (the recogniser doesn't hear aspiration, retroflex or length reliably),
then aligned: missing vowels and consonants are what the owner hears as "swallowed".
Checked on 998 clips of rounds r20-r27, es1, es2, es5 with the owner's votes: in a phrase, the clip the owner rated
best has fewer mismatches than the one rated bad in 68% of pairs, and "bad" clips miss twice as many vowels.
So: a filter for gross errors (swallowed vowels, v heard as m, a vanished sound), not a judge of quality.
Usage: python3 ears.py [heard.json] -> out/ears/scored.json
"""
import json
import sys

CLASSES = [('aʌəɐɑæ', 'a'), ('iɪy', 'i'), ('uʊɯ', 'u'), ('eɛ', 'e'), ('oɔ', 'o'),
           ('kgɡqx', 'K'), ('cɟʧʤ', 'C'), ('tdʈɖθð', 'T'), ('pbfɸβ', 'P'), ('mnɳɲŋ', 'N'),
           ('rɾɹɽʀʁ', 'R'), ('lɭʎ', 'L'), ('ʋvw', 'V'), ('j', 'Y'), ('szʃʒɕʑ', 'S'), ('hɦ', 'H')]
MAP = {c: k for chars, k in CLASSES for c in chars}
VOWELS = set('aiueo')


def broad(ipa):
    """IPA string -> list of broad classes; affricates tʃ/dʒ count once, length/stress/aspiration dropped."""
    s = ipa.replace('tʃ', 'ʧ').replace('dʒ', 'ʤ').replace(' ', '')
    out = []
    for c in s:
        k = MAP.get(c)
        if k and not (out and out[-1] == k and k not in VOWELS):  # doubled consonant = one
            out.append(k)
    return out


def align(a, b):
    """Levenshtein with backtrace: returns (distance, [(expected, heard or '-')] for every mismatch)."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    i, j, diff = n, m, []  # diff: (expected class, heard class or '-') where they differ
    while i and j:
        if d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            if a[i - 1] != b[j - 1]:
                diff.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif d[i][j] == d[i - 1][j] + 1:
            diff.append((a[i - 1], '-')); i -= 1
        else:
            j -= 1
    diff += [(x, '-') for x in a[:i]]
    return d[n][m], diff[::-1]


def score(expected, heard):
    a, b = broad(expected), broad(heard.replace(' ', ''))
    dist, diff = align(a, b)
    return {'err': round(dist / max(len(a), 1), 3), 'missing_vowels': sum(e in VOWELS and h == '-' for e, h in diff),
            'diff': ' '.join(f'{e}>{h}' for e, h in diff)}


assert broad('sʌhʌɡʌtaː') == ['S', 'a', 'H', 'a', 'K', 'a', 'T', 'a']
assert score('sʌhʌɡʌtaː', 's a h g a t a')['missing_vowels'] == 1  # "сахгата": the second a swallowed
assert score('dˈʊkkʰʌŋ', 'd u k a n')['err'] == 0
assert score('bʰʌɡʌʋʌtaː', 'b a ɡ a m a t a')['diff'] == 'V>N'  # es1: «ма вместо ва»

if __name__ == '__main__':
    heard = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'out/ears/heard.json', encoding='utf-8'))
    for h in heard:
        h.update(score(h['expected'], h['heard']))
    json.dump(heard, open('out/ears/scored.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(heard), 'clips scored')
