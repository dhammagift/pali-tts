"""Predict where pratham will misread Pali, before anyone listens.

The model's own duration predictor (models/hi_IN-pratham-medium.align.onnx, see round26.py) says how long every
phoneme of our IPA will last. A sound the voice swallows or cuts gets a near-zero duration, and a word whose
durations jump between runs (the noise_w the voice is rendered with) comes out differently from take to take.
Both are measured per word: a few runs with the rounds' settings (0.7x), shortest vowel, shortest consonant,
the last sound before a pause, and the spread of the word's length between runs.

Checked against the owner's votes of all listening rounds (votes/rNN.jsonl, out/rNN/index.json): a rated
best/ok is good; bad, or not rated at all, is bad (owner: a variant left unrated was not good).

Usage (f3, .venv):
  python3 risk.py eval [votes_dir]     how well the score separates the owner's bad from good
  python3 risk.py scan sutta.json ...  rank the words of SuttaCentral root texts by risk
"""
import collections
import glob
import json
import re
import sys

import numpy as np

from pali_ipa import to_ipa, tune

MODEL = 'models/hi_IN-pratham-medium.onnx'
ALIGN = 'models/hi_IN-pratham-medium.align.onnx'  # made by round26.align_model()
CFG = json.load(open(MODEL + '.json'))
IDS = CFG['phoneme_id_map']
MS = 256 / 22050 * 1000  # one duration frame
LENGTH = 1.15 / 0.7
RUNS = 3
VOWELS = set('aʌəeɛiɪoɔuʊ')
MODS = set('ːʰ̃ʲ')
PUNCT = set(',.?!:;')
_session = None


def durations(ipa):
    """ms per character of ipa (each phoneme with the pad after it), for one run of the duration predictor."""
    global _session
    if _session is None:
        import onnxruntime as ort  # not needed by gop.py, which imports labelled() from here
        _session = ort.InferenceSession(ALIGN, providers=['CPUExecutionProvider'])
    chars = [c for c in ipa if c in IDS]
    ids = IDS['^'] + IDS['_']
    for c in chars:
        ids += IDS[c] + IDS['_']
    ids += IDS['$']
    _, dur = _session.run(None, {'input': np.array([ids], dtype=np.int64),
                                'input_lengths': np.array([len(ids)], dtype=np.int64),
                                'scales': np.array([0.667, LENGTH, 0.8], dtype=np.float32)})
    dur = dur.reshape(-1) * MS
    return chars, [dur[2 + 2 * j] + dur[3 + 2 * j] for j in range(len(chars))]


def segments(chars):
    """Group characters into sounds: a letter with the modifiers after it, a stress mark joins the next letter.
    -> list of (word index, sound string, [char indices])."""
    out, word, pending = [], 0, []
    for j, c in enumerate(chars):
        if c == ' ':
            word += 1
        elif c in PUNCT:
            out.append((word, c, [j]))
        elif c == 'ˈ':
            pending.append(j)
        elif c in MODS and out and out[-1][1] not in PUNCT and out[-1][0] == word:
            w, s, js = out[-1]
            out[-1] = (w, s + c, js + [j])
        else:
            out.append((word, c, pending + [j]))
            pending = []
    return out


def word_features(ipa):
    """Per word: shortest vowel, shortest consonant, the sound before a pause (ms), spread of the word's length
    between runs (coefficient of variation). Means over RUNS runs, minima over runs for the shortest sounds."""
    runs = [durations(ipa) for _ in range(RUNS)]  # noise_w is drawn inside the graph: every run differs
    chars = runs[0][0]
    segs = segments(chars)
    nwords = ipa.count(' ') + 1
    feats = []
    for w in range(nwords):
        ws = [s for s in segs if s[0] == w and s[1] not in PUNCT]
        if not ws:
            feats.append(None)
            continue
        per_run = np.array([[sum(d[j] for j in js) for _, _, js in ws] for _, d in runs])  # runs x sounds
        vow = [i for i, (_, s, _) in enumerate(ws) if s[0] in VOWELS]
        con = [i for i in range(len(ws)) if i not in vow]
        last = segs.index(ws[-1])
        before_pause = last + 1 == len(segs) or segs[last + 1][1] in PUNCT
        total = per_run.sum(1)
        feats.append({
            'vmin': float(per_run[:, vow].min()) if vow else 999.0,
            'cmin': float(per_run[:, con].min()) if con else 999.0,
            'final': float(per_run[:, -1].min()) if before_pause else 999.0,
            'cv': float(total.std() / total.mean()),
        })
    return feats


def risk(f):
    """One number per word, higher = more likely misread. Weights are set by `eval`, not tuned per word."""
    if f is None:
        return 0.0
    return max(0.0, 45 - f['vmin']) + 0.5 * max(0.0, 25 - f['cmin']) + max(0.0, 70 - f['final']) + 200 * f['cv']


def labelled(votes_dir='votes', files=False):
    """(round, phrase id, variant sent IPA, good?) for every variant of every rNN round. Last click wins."""
    out = []
    for path in sorted(glob.glob(f'{votes_dir}/r*.jsonl')):
        rnd = path.split('/')[-1][:-6]
        if not re.fullmatch(r'r\d+b?', rnd):
            continue
        try:
            idx = json.load(open(f'out/{rnd}/index.json', encoding='utf-8'))
        except FileNotFoundError:
            continue
        rating = collections.defaultdict(dict)
        for line in open(path, encoding='utf-8'):
            try:
                v = json.loads(line)
            except ValueError:
                continue
            if v['kind'] == 'rating':
                rating[v['phrase']][v['variant']] = v['value']
        for sec in idx['sections']:
            for p in sec['phrases']:
                if not rating.get(p['id']):
                    continue  # phrase never listened to (or an open round): no labels
                for v in p['variants']:
                    if 'sent' in v and re.search(r'[ˈʌː]', v['sent']):  # our IPA (not Google/espeak text)
                        good = rating[p['id']].get(v['id']) in ('best', 'ok')
                        out.append((rnd, p['id'], v['sent'], good) + ((v['file'],) if files else ()))
    return out


def evaluate(votes_dir='votes'):
    """Pairs inside a phrase whose IPA differs and whose labels differ: does the bad one score higher?
    The score of a variant is the max risk over the words that differ between that phrase's variants."""
    data = labelled(votes_dir)
    by_phrase = collections.defaultdict(list)
    for rnd, pid, sent, good in data:
        by_phrase[(rnd, pid)].append((sent, good))
    cache, feats, hits, pairs = {}, {}, 0, 0
    labelled_pairs = []
    for vs in by_phrase.values():
        sents = sorted({s for s, _ in vs})
        if len(sents) < 2:
            continue
        words = [s.split(' ') for s in sents]
        if len({len(w) for w in words}) != 1:
            diff = None  # different word count: score the whole phrase
        else:
            diff = [i for i in range(len(words[0])) if len({w[i] for w in words}) > 1]
        for s in sents:
            if s not in cache:
                fs = word_features(s)
                ws = [fs[i] for i in (diff if diff else range(len(fs))) if fs[i]]
                cache[s] = max(risk(f) for f in ws)
                feats[s] = {k: min(f[k] for f in ws) if k != 'cv' else max(f[k] for f in ws) for k in ws[0]}
        for a, ga in vs:
            for b, gb in vs:
                if ga and not gb and a != b:
                    labelled_pairs.append((a, b))
                    pairs += 1
                    hits += (cache[b] > cache[a]) + 0.5 * (cache[b] == cache[a])
    print(f'{len(data)} variants, {len(by_phrase)} phrases, {pairs} good/bad pairs with different IPA: '
          f'bad scored higher in {hits / max(pairs, 1):.0%}')
    for k in next(iter(feats.values())):  # each feature alone: lower duration / higher spread = riskier?
        sign = -1 if k != 'cv' else 1
        acc = sum((sign * feats[b][k] > sign * feats[a][k]) + 0.5 * (feats[b][k] == feats[a][k]) for a, b in labelled_pairs)
        print(f'  {k}: bad riskier in {acc / max(pairs, 1):.0%}')
    json.dump({'feats': feats, 'pairs': labelled_pairs}, open('out/risk_eval.json', 'w', encoding='utf-8'), ensure_ascii=False)


def scan(paths, top=100):
    """Rank the distinct words of root texts by risk; each word is scored inside its first segment."""
    seen = {}
    for path in paths:
        for text in json.load(open(path, encoding='utf-8')).values():
            text = text.strip()
            if not text:
                continue
            ipa = tune(to_ipa(text, full_a=True))
            words = re.findall(r"[^\s—–]+", text)
            fs = word_features(ipa)
            if len(fs) != len(words):
                continue
            for w, f in zip(words, fs):
                key = re.sub(r'[^\w]', '', w.lower())
                if key and key not in seen:
                    seen[key] = (risk(f), w, f)
    for score, w, f in sorted(seen.values(), key=lambda x: -x[0])[:top]:
        print(f'{score:6.1f}  {w:28} ' + ' '.join(f'{k}={v:.0f}' if k != 'cv' else f'cv={v:.2f}' for k, v in f.items()))


if __name__ == '__main__':
    assert [s[1] for s in segments(list('kˈaːjən, bʰə'))] == ['k', 'aː', 'j', 'ə', 'n', ',', 'bʰ', 'ə']
    if sys.argv[1:2] == ['eval']:
        evaluate(*sys.argv[2:3])
    elif sys.argv[1:2] == ['scan']:
        scan(sys.argv[2:])
