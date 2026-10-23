"""Round miles6 (owner 2026-10-23, Yojanāni: «by name-matter» read «ай» - the b at a line's start swallowed): the voice
from ryan cuts a line's first sound as it cut its last one (round miles5: saved by a tail). The same at the start: a
head word read before the line and cut where the model's own durations say the line starts.
As now (tail only) / head + tail; SN 12.2 lines of DG's own translation, which all start with "by". Blind.
Usage (on f3): .venv/bin/python round_miles6.py -> out/miles6/; then build_page.py with ROUND = 'miles6'
"""
import json
import os
import re

import numpy as np
from piper import PiperVoice

from round_miles2 import CFG, en_expand, en_phonemes
from round_miles5 import CARRIER, HOP, V1, align
from round_st1 import mp3

OUT = 'out/miles6'
HEAD = 'ænd '  # "and": the line's first sound is no longer the model's first
TEXTS = ['By non-discernment conditioned, monks, are constituents;', 'by attention conditioned is name-matter;',
         'by name-matter conditioned is the six-fold area;', 'by contact conditioned is feeling;']


def read(voice, sess, text, head):
    sr, parts = voice.config.sample_rate, []
    for sent in re.split(r'(?<=[.?!;:])\s+', en_expand(text).strip()):
        ph = en_phonemes(voice, sent)
        ids = voice.phonemes_to_ids(list(head) + ph + list(CARRIER))
        audio, dur = sess.run(None, {'input': np.array([ids], dtype=np.int64), 'input_lengths': np.array([len(ids)], dtype=np.int64),
                                     'scales': np.array([CFG.noise_scale, CFG.length_scale, CFG.noise_w_scale], dtype=np.float32)})
        audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
        starts = np.concatenate([[0], np.cumsum(dur)])
        a = max(starts[2 + 2 * len(head)] - int(0.03 * sr), 0) if head else 0
        a_ = audio[a:starts[2 + 2 * (len(head) + len(ph) + 1)]].astype(np.float32)
        fade = int(0.03 * sr)
        a_[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        parts += [np.zeros(int(sr * 0.15), np.float32), a_, np.zeros(int(sr * 0.35), np.float32)]
    return np.concatenate(parts), sr


if __name__ == '__main__':
    v1, sess = PiperVoice.load(V1, config_path=V1 + '.json'), align(V1)
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, label, head in [('a', 'как сейчас', ''), ('b', 'с началом', HEAD)]:
            f = f'en{i}.{vid}.mp3'
            mp3(*read(v1, sess, text, head), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучше; ✓ правильно; ✗ неправильно (слышно ли «b» в начале)'})
    json.dump({'round': 'miles6', 'sections': [{'id': 'en', 'title': 'Yojanāni: «by» в начале строки', 'multi_best': False,
                                                'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
