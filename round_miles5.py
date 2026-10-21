"""Round miles5 (Miles 2026-10-21 on miles4: «the voice with the endings cut is much higher quality except for the fact
that it cuts off the endings»): keep that voice (v1, from ryan, models/en_miles-medium) and save its endings at
synthesis time: each sentence is read with a carrier word after it ("... end. And") and cut where the model's own
durations say the carrier starts, so the last real sound is no longer the model's last (ryan cuts its last sound).
Against the voice now in DG (en_miles2, from joe). Blind, miles4's lines.
Usage (on f3): .venv/bin/python round_miles5.py -> out/miles5/; then build_page.py with ROUND = 'miles5', LANG = 'en'
"""
import json
import os
import re

import numpy as np
import onnx
import onnxruntime as ort
from piper import PiperVoice

from round_miles2 import CFG, en_expand, en_phonemes, read
from round_miles4 import TEXTS
from round_st1 import mp3

OUT = 'out/miles5'
V1 = 'models/en_miles-medium.onnx'
CARRIER = ' ænd'  # "and": the sentence's last sound is followed by more speech, so it is read whole
HOP = 256


def align(model):
    """The model with its duration node (/Ceil) as a second output, like round26.align_model()."""
    path = model[:-5] + '.align.onnx'
    if not os.path.exists(path):
        m = onnx.load(model)
        m.graph.output.append(onnx.helper.make_tensor_value_info('/Ceil_output_0', onnx.TensorProto.FLOAT, None))
        onnx.save(m, path)
    return ort.InferenceSession(path, providers=['CPUExecutionProvider'])


def read_carried(voice, sess, text):
    sr, parts = voice.config.sample_rate, []
    for sent in re.split(r'(?<=[.?!;:])\s+', en_expand(text).strip()):
        ph = en_phonemes(voice, sent)
        ids = voice.phonemes_to_ids(ph + list(CARRIER))
        assert len(ids) == 2 * len(ph + list(CARRIER)) + 3, 'ids are ^ _ (p _)* $'
        audio, dur = sess.run(None, {'input': np.array([ids], dtype=np.int64), 'input_lengths': np.array([len(ids)], dtype=np.int64),
                                     'scales': np.array([CFG.noise_scale, CFG.length_scale, CFG.noise_w_scale], dtype=np.float32)})
        audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
        starts = np.concatenate([[0], np.cumsum(dur)])
        end = starts[2 + 2 * (len(ph) + 1)]  # the carrier's first sound (after its space)
        a = audio[:end].astype(np.float32)
        fade = int(0.03 * sr)
        a[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        parts += [a, np.zeros(int(sr * 0.35), np.float32)]
    return np.concatenate(parts), sr


if __name__ == '__main__':
    v1 = PiperVoice.load(V1, config_path=V1 + '.json')
    now = PiperVoice.load('models/en_miles2-medium.onnx', config_path='models/en_miles2-medium.onnx.json')
    sess = align(V1)
    variants = [('a', lambda t: read_carried(v1, sess, t)), ('b', lambda t: read(now, t))]  # labels hidden: blind
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, fn in variants:
            f = f'en{i}.{vid}.mp3'
            mp3(*fn(text), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': vid.upper(), 'file': f, 'sent': text})
        phrases.append({'id': f'en{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ best; ✓ ok; ✗ bad (say why: endings cut, quality...). Tap a word that is read wrong'})
    json.dump({'round': 'miles5', 'sections': [{'id': 'en', 'title': 'Yojanāni: which sounds better? Listen to the line ends too',
                                                'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
