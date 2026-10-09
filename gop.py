"""Ears, take 2: how sure a phoneme recogniser is that it hears each sound we asked for (goodness of pronunciation).

ears.py lets the recogniser (wav2vec2-lv-60-espeak-cv-ft) write down what it hears and compares the two strings in
broad classes: it hears no aspiration, retroflex or length, and in rounds 20-27 it told bad from good in 68% of
pairs. Here the recogniser is instead forced through the IPA we sent (CTC Viterbi alignment), and every sound gets
mean over its frames of log p(that sound) - log p(the best other sound). Its vocabulary has ʈ ʈʰ pʰ f ɳ ɲ ʌ aː...,
so "pʰ heard as f" or "a swallowed" shows as a sound with a low score, and the frame argmax says what it heard.

Usage (f3, .venv-ears with torch + transformers):
  python3 gop.py eval [votes_dir]   score every voted clip, pairs bad/good as risk.py eval -> out/gop_eval.json
  python3 gop.py clip file.mp3 'IPA'
"""
import collections
import json
import re
import subprocess
import sys

import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

from risk import labelled

NAME = 'facebook/wav2vec2-lv-60-espeak-cv-ft'
torch.set_num_threads(2)
PROC = Wav2Vec2Processor.from_pretrained(NAME, do_phonemize=False)
MODEL = Wav2Vec2ForCTC.from_pretrained(NAME).eval()
VOCAB = PROC.tokenizer.get_vocab()
BLANK = VOCAB['<pad>']
SKIP = set('ˈˌ ,.?!:;—–')
SAME = {'ɦ': 'h', 'ʧ': 'tʃ', 'ʤ': 'dʒ'}  # our symbol -> the recogniser's


def tokens(ipa):
    """Our IPA -> recogniser tokens, longest match first; a long consonant is the plain one (its vocabulary has
    few geminates), a repeated sound (oːoːoː, jj) is one token. -> [(token id, word index)]"""
    ipa = re.sub(r'(?<=[^aeiouʌɪʊəɛɔ])ː', '', ipa)
    out, word, i = [], 0, 0
    while i < len(ipa):
        c = ipa[i]
        if c == ' ':
            word += 1
        if c in SKIP:
            i += 1
            continue
        for n in (3, 2, 1):
            t = ''.join(SAME.get(x, x) for x in ipa[i:i + n])
            if t in VOCAB:
                break
        else:
            i += 1  # a symbol the recogniser has no token for (ː after a consonant, ̃)
            continue
        if not (out and out[-1][0] == VOCAB[t] and out[-1][1] == word):
            out.append((VOCAB[t], word))
        i += n
    return out


def logprobs(path):
    audio = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                           capture_output=True, check=True).stdout
    x = PROC(np.frombuffer(audio, dtype=np.float32), sampling_rate=16000, return_tensors='pt').input_values
    with torch.no_grad():
        return torch.log_softmax(MODEL(x).logits[0], -1).numpy()


def force_align(lp, seq):
    """CTC Viterbi: frames -> state path over blank, s1, blank, s2, ... -> list of frame lists, one per token."""
    states = [BLANK]
    for s in seq:
        states += [s, BLANK]
    S, T = len(states), len(lp)
    NEG = -1e9
    d = np.full((T, S), NEG)
    back = np.zeros((T, S), dtype=np.int8)
    d[0, 0] = lp[0, states[0]]
    if S > 1:
        d[0, 1] = lp[0, states[1]]
    for t in range(1, T):
        for s in range(S):
            best, k = d[t - 1, s], 0
            if s >= 1 and d[t - 1, s - 1] > best:
                best, k = d[t - 1, s - 1], 1
            if s >= 2 and states[s] != BLANK and states[s] != states[s - 2] and d[t - 1, s - 2] > best:
                best, k = d[t - 1, s - 2], 2
            d[t, s], back[t, s] = best + lp[t, states[s]], k
    s = S - 1 if S == 1 or d[T - 1, S - 1] >= d[T - 1, S - 2] else S - 2
    frames = [[] for _ in seq]
    for t in range(T - 1, -1, -1):
        if s % 2:
            frames[s // 2].append(t)
        s -= int(back[t, s])
    return frames


INV = None


def score(path, ipa):
    """-> per token (token, word, gop, heard): gop = mean over its frames of log p(token) - log p(best other token)."""
    global INV
    INV = INV or {v: k for k, v in VOCAB.items()}
    toks = tokens(ipa)
    lp = logprobs(path)
    seq = [t for t, _ in toks]
    if len(seq) * 2 + 1 > len(lp):
        return [(INV[t], w, -20.0, '?') for t, w in toks]
    out = []
    for (t, w), fr in zip(toks, force_align(lp, seq)):
        other = lp[fr].copy()
        other[:, [t, BLANK]] = -1e9
        out.append((INV[t], w, float(np.mean(lp[fr, t] - other.max(1))), INV[int(other[:, :].max(0).argmax())]))
    return out


def evaluate(votes_dir='votes'):
    """Score every voted clip (slow: ~3 s a clip on f3) -> out/gop_eval.json, then report()."""
    clips = {}
    for i, (rnd, pid, sent, good, f) in enumerate(labelled(votes_dir, files=True)):
        clips[f'out/{rnd}/{f}'] = {'phrase': f'{rnd}/{pid}', 'good': good, 'ipa': sent, 'sounds': score(f'out/{rnd}/{f}', sent)}
        if i % 50 == 49:
            print(i + 1, 'clips', flush=True)
    json.dump(clips, open('out/gop_eval.json', 'w', encoding='utf-8'), ensure_ascii=False)
    report(clips)


def report(clips=None):
    """A sound's score minus that sound's median over all clips (ʋ is always low: the recogniser expects v), lowest
    over the words that differ between a phrase's variants. Pairs good/bad inside a phrase: is the bad one lower?"""
    clips = clips or json.load(open('out/gop_eval.json', encoding='utf-8'))
    per = collections.defaultdict(list)
    for c in clips.values():
        for t, _, g, _ in c['sounds']:
            per[t].append(g)
    med = {t: float(np.median(v)) for t, v in per.items()}
    by_phrase = collections.defaultdict(list)
    for c in clips.values():
        by_phrase[c['phrase']].append(c)
    for norm in (False, True):
        for agg in (min, np.mean):
            hits = pairs = same = same_hits = 0
            for vs in by_phrase.values():
                words = [c['ipa'].split(' ') for c in vs]
                diff = None
                if len({len(w) for w in words}) == 1 and len({c['ipa'] for c in vs}) > 1:
                    diff = {i for i in range(len(words[0])) if len({w[i] for w in words}) > 1}
                val = []
                for c in vs:
                    xs = [g - med[t] * norm for t, w, g, _ in c['sounds'] if diff is None or w in diff] or [0.0]
                    val.append(float(agg(xs)))
                for a, ca in zip(val, vs):
                    for b, cb in zip(val, vs):
                        if ca['good'] and not cb['good']:
                            pairs += 1
                            hits += (b < a) + 0.5 * (b == a)
                            if ca['ipa'] == cb['ipa']:  # two takes of the same IPA: only the noise differs
                                same += 1
                                same_hits += (b < a) + 0.5 * (b == a)
            print(f"{'normalised' if norm else 'raw':10} {agg.__name__:5}: {pairs} pairs, bad lower in {hits / max(pairs, 1):.0%}"
                  f"; same IPA {same} pairs, {same_hits / max(same, 1):.0%}")


if __name__ == '__main__':
    assert [t for t, _ in tokens('pʰoʈːʰʌ ɟˈʌɾaː')] == [VOCAB[x] for x in ['pʰ', 'o', 'ʈʰ', 'ʌ', 'ɟ', 'ʌ', 'ɾ', 'aː']], tokens('pʰoʈːʰʌ ɟˈʌɾaː')
    if sys.argv[1:2] == ['eval']:
        evaluate(*sys.argv[2:3])
    elif sys.argv[1:2] == ['report']:
        report()
    elif sys.argv[1:2] == ['clip']:
        for x in score(sys.argv[2], sys.argv[3]):
            print(f'{x[0]:4} w{x[1]} {x[2]:6.1f}  heard {x[3]}')
