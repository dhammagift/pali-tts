"""Round 26: word-final ṁ faked. pratham learned [ŋ] only before k/g (Hindi), so ŋŋ, ŋ, m and a nasal vowel
all came out as "m" or "n" (round 24). Here the voice gets ŋɡ / ŋk - a velar nasal it knows - and the g / k
is cut out of the audio afterwards, using the per-phoneme durations the model computes internally
(its /Ceil node, exposed as an extra output in models/hi_IN-pratham-medium.align.onnx).
Usage: .venv/bin/python round26.py -> out/r26/*.mp3, out/r26/index.json
"""
import json
import os
import re
import subprocess

import numpy as np
import onnx
import onnxruntime as ort
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r26'
LENGTH = 1.15 / 0.875
MODEL = 'models/hi_IN-pratham-medium.onnx'
ALIGN = 'models/hi_IN-pratham-medium.align.onnx'
FINAL = re.compile(r'ŋŋ(?=[ ,.?!:;]|$)')
TEXTS = ['Jarāpi dukkhā, maraṇampi dukkhaṁ.', 'Atthi imasmiṁ kāye.', 'Nimmānaratī devā saddamanussāvesuṁ.']


def align_model():
    if not os.path.exists(ALIGN):
        m = onnx.load(MODEL)
        m.graph.output.append(onnx.helper.make_tensor_value_info('/Ceil_output_0', onnx.TensorProto.FLOAT, None))
        onnx.save(m, ALIGN)
    return ort.InferenceSession(ALIGN, providers=['CPUExecutionProvider'])


CFG = json.load(open(MODEL + '.json'))
IDS = CFG['phoneme_id_map']
HOP = 256
SESSION = align_model()


def synth_cut(phonemes, cut, ns=0.6, nw=0.7):
    """phonemes: list of symbols; cut: indices of phonemes whose sound is removed from the result."""
    ids = IDS['^'] + IDS['_']
    for p in phonemes:
        ids += IDS[p] + IDS['_']
    ids += IDS['$']
    audio, dur = SESSION.run(None, {'input': np.array([ids], dtype=np.int64),
                                    'input_lengths': np.array([len(ids)], dtype=np.int64),
                                    'scales': np.array([ns, LENGTH, nw], dtype=np.float32)})
    audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
    starts = np.concatenate([[0], np.cumsum(dur)[:-1]])
    keep = np.ones(len(audio), dtype=bool)
    fade = int(0.008 * 22050)
    for j in cut:
        k = 2 + 2 * j  # ids: ^ _ (p _)* $ - phoneme j sits at 2 + 2j, its pad right after
        a, b = starts[k], starts[k] + dur[k] + dur[k + 1] // 2
        if a > fade:
            audio[a - fade:a] *= np.linspace(1, 0, fade)
        keep[a:b] = False
    return audio[keep]


def render(audio, f):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-q:a', '7', f], input=audio.astype(np.float32).tobytes(), check=True)


def variant(ipa, stop, cut):
    s = FINAL.sub('ŋ' + stop, ipa) if stop else ipa
    ph = list(s)
    idx = [i for i, p in enumerate(ph) if p == stop and i > 0 and ph[i - 1] == 'ŋ' and (i + 1 == len(ph) or ph[i + 1] in ' ,.?!:;')] if cut else []
    return s, ph, idx


if __name__ == '__main__':
    own = PiperVoice.load('models/pali_dg-medium.onnx')
    os.makedirs(OUT, exist_ok=True)
    V = [('a', 'как сейчас (ŋŋ)', '', False), ('b', '«ŋɡ», «г» вырезано', 'ɡ', True),
         ('c', '«ŋk», «к» вырезано', 'k', True), ('d', '«ŋɡ» целиком (явное «нг»)', 'ɡ', False)]
    phrases = []
    for n, text in enumerate(TEXTS):
        base = tune(to_ipa(text, full_a=True))
        vs = []
        for vid, label, stop, cut in V:
            s, ph, idx = variant(base, stop, cut)
            assert not cut or idx, (text, s)
            for take in (1, 2):
                f = f'p{n}.{vid}{take}.mp3'
                render(synth_cut(ph, idx), f'{OUT}/{f}')
                vs.append({'id': f'{vid}{take}', 'label': f'pratham: {label} · дубль {take}', 'file': f, 'sent': s})
        audio = own.phoneme_ids_to_audio(own.phonemes_to_ids(list(to_ipa(text, full_a=True))), SynthesisConfig(length_scale=1.0 / 0.875, noise_scale=0.6, noise_w_scale=0.7))
        render(audio, f'{OUT}/p{n}.own.mp3')
        vs.append({'id': 'own', 'label': 'свой голос, для сравнения', 'file': f'p{n}.own.mp3', 'sent': ''})
        phrases.append({'id': f'p{n}', 'text': text, 'ipa': base, 'script': '', 'variants': vs,
                        'note': '★ где конечное ṁ звучит как настоящее носовое «нг» (dukkhaṁ, imasmiṁ, -suṁ), без «м»/«н» и без лишнего «г»'})
        print(n, flush=True)
    json.dump({'round': 'r26', 'sections': [{'id': 'm', 'title': 'Конечное ṁ: «нг» без «г»', 'multi_best': False,
                                              'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
