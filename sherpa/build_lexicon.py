"""Pali lexicon for sherpa-onnx (new format: `word || phones`), from every word form in the SC Pali canon.
Phones are exactly what our server feeds hi_IN-pratham: tune(to_ipa(word, full_a=True)), one codepoint per phone.
Usage: venv python build_lexicon.py /root/sherpa-pi/canon out/lexicon-pi.txt"""
import glob, json, re, subprocess, sys, unicodedata
from collections import Counter

sys.path.insert(0, '/var/www/pali-tts')
from pali_ipa import to_ipa, tune

canon, out = sys.argv[1], sys.argv[2]
pmap = json.load(open('/var/www/pali-tts/models/hi_IN-pratham-medium.onnx.json'))['phoneme_id_map']
WORD = re.compile(r'[a-zāīūṭḍṅñṇḷṁṃ]+')
SHERPA_SPLIT = re.compile(r'[\s,;:.!?]+')   # how TokenizeFromLexicon cuts text into words

words, raw, parts = Counter(), Counter(), Counter()
for f in glob.glob(f'{canon}/**/*.json', recursive=True):
    part = f[len(canon):].strip('/').split('/')[0]
    for seg in json.load(open(f, encoding='utf-8')).values():
        text = unicodedata.normalize('NFC', seg).lower()
        for w in WORD.findall(text):
            words[w] += 1
            parts[part] += 1
        raw.update(t for t in SHERPA_SPLIT.split(text) if t and not WORD.fullmatch(t))

def phones(w):
    # As inside a phrase (a word follows): rules that depend on the next word, like the word-final o held long
    # (round 40), then apply as they do mid-sentence, which is where most words stand. A lexicon entry cannot see
    # its context, so before a full stop that o comes out longer than our server makes it (~575 vs ~330 ms at 0.7x).
    return tune(to_ipa(w, full_a=True) + ' ').rstrip(' ')

lines, dropped, rev = [], [], 0
for w in sorted(words):
    p = phones(w)
    bad = sorted({c for c in p if c not in pmap or c == ' '})
    if bad:
        dropped.append((w, p, bad))
        continue
    lines.append(f'{w} || {" ".join(p)}')
    # sherpa lowercases with towlower(), which in the C locale leaves Ā, Ñ, Ī... as they are: list those capitalised too
    if not w[0].isascii():
        lines.append(f'{w[0].upper() + w[1:]} || {" ".join(p)}')
        if 'ṁ' in w:
            lines.append(f'{(w[0].upper() + w[1:]).replace("ṁ", "ṃ")} || {" ".join(p)}')
    if 'ṁ' in w:  # VRI/CST texts and most Pali apps write the niggahita as ṃ
        lines.append(f'{w.replace("ṁ", "ṃ")} || {" ".join(p)}')
# "…pe…" / "…pa…" (a passage left out) is one token to sherpa: read it as our server does, ", peyyāla,"
for k in ('…pe…', '…pa…'):
    lines.append(f'{k} || , {" ".join(phones(k))} ,')

header = [
    '# Lexicon: word(s) || space-separated phones',
    '# Pali (IAST, lowercase, NFC, niggahita as ṁ, also listed with ṃ and, for a non-ASCII initial, capitalised) for vits-piper-pi-pratham (hi_IN-pratham voice).',
    '# Phones: Dhamma.Gift IAST->IPA rules (pali_ipa.py to_ipa(full_a=True) + tune), tuned in blind listening rounds.',
    f'# Source: every word form of the Pali Tipiṭaka (Mahāsaṅgīti, bilara-data root/pli/ms: {", ".join(f"{k} {v}" for k, v in sorted(parts.items()))} tokens)',
    f'# Entries: {len(lines)}',
    '#',
]
open(out, 'w', encoding='utf-8').write('\n'.join(header + lines) + '\n')
print('distinct words', len(words), 'tokens', sum(words.values()), 'entries', len(lines), 'dropped', len(dropped))
for d in dropped[:20]: print('DROP', d)
print('raw sherpa tokens with punctuation inside/attached (distinct):', len(raw), 'occurrences', sum(raw.values()))
for t, n in raw.most_common(25): print('  RAW', repr(t), n)
nm = sum(1 for w in words if 'ṃ' in w); print('words already with ṃ:', nm)
