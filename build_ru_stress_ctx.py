"""ru_stress_ctx.json for respell.ru_context_stress (service) and web/pali-tts.js (offline), from RUAccent over every
Russian line DG shows (Kaggle ru-accent: ru-accented.tsv, '+' before the stressed vowel) against the stress our
phonemes give the same lines without the table (espeak + names list + RU_STRESS + ё).
  word: RUAccent's most frequent reading of a word, where espeak's differs (бо́льшим -> больши́м, бу́дешь, дела́);
  ctx:  the other places of words RUAccent reads two ways: "prev word next" -> the majority form there, where it differs
        from the word's own (дела́ его, в благо́м уделе; and де́ла where дела́ is the rule).
Left out: one-syllable words, words we stress ourselves (RU_ACCENT, RU_STRESS, ё), -ого/-его/сегодня (marked, espeak
reads г), hyphen compounds. Owner 2026-11-17: the October audit (ru_stress_audit.tsv) found ~1400 such words and only
~75 were fixed by hand; this takes them all, with context.
Usage: .venv/bin/python build_ru_stress_ctx.py ru-lines.tsv ru-accented.tsv
"""
import collections
import json
import sys

from piper import PiperVoice

import respell
from ru_stress_check import VOW, espeak_stress, marked_stress


def form(w, i):
    out, n = [], 0
    for c in w:
        out.append(c)
        if c in VOW:
            if n == i:
                out.append('́')
            n += 1
    return ''.join(out)


if __name__ == '__main__':
    respell.RU_CTX = {'word': {}, 'ctx': {}}  # our stress without the table
    voice = PiperVoice.load('models/ru_owner_h3-medium.onnx')
    plain = dict(l.rstrip('\n').split('\t', 1) for l in open(sys.argv[1], encoding='utf-8') if '\t' in l)
    acc = dict(l.rstrip('\n').split('\t', 1) for l in open(sys.argv[2], encoding='utf-8') if '\t' in l)
    reads, ctx_reads, ours = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter), {}
    used = 0
    for n, (key, text) in enumerate(plain.items()):
        if n % 10000 == 0:
            print(n, used, file=sys.stderr, flush=True)
        a = acc.get(key, '')
        if not a or a.startswith('!'):
            continue
        e, m = espeak_stress(voice, text), marked_stress(a)
        if e is None or len(e) != len(m) or any(x[0] != y[0] for x, y in zip(e, m)):
            continue
        used += 1
        for i, ((w, ei), (_, mi)) in enumerate(zip(e, m)):
            if (mi is None or '-' in w or 'ё' in w or sum(c in VOW for c in w) < 2 or w in respell.RU_ACCENT
                    or w in respell.RU_STRESS or w.endswith(('ого', 'его')) or w.startswith('сегодн')):
                continue
            ours.setdefault(w, ei)
            reads[w][mi] += 1
            ctx_reads[(e[i - 1][0] if i else '', w, e[i + 1][0] if i + 1 < len(e) else '')][mi] += 1
    word, ctx, main = {}, {}, {}
    for w, r in reads.items():  # the word's own reading: RUAccent's most frequent one (better than espeak's guess anywhere)
        mi = main[w] = r.most_common(1)[0][0]
        if mi != ours[w]:
            word[w] = form(w, mi)
    for (p, w, nx), r in ctx_reads.items():  # the other places, by their neighbours
        if len(reads[w]) > 1:
            mi = r.most_common(1)[0][0]
            if mi != main[w]:
                ctx[f'{p} {w} {nx}'] = form(w, mi)
    json.dump({'word': dict(sorted(word.items())), 'ctx': dict(sorted(ctx.items()))},
              open('ru_stress_ctx.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{used} of {len(plain)} lines aligned; word {len(word)}, ctx {len(ctx)}')
