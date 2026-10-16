"""Does a Russian Piper voice put the stress where its input says, without anyone listening (owner 2026-10-16: «задача
починить», no more ear checks)? The voice's own duration predictor (round26-style .align model: /Ceil as an extra
output, noise off, length x4 for finer frames) tells how long it holds each vowel; in every word of 2+ vowels the stressed one (after ˈ in our
phonemes) should be the longest. Prints the share of words where it isn't, and those words.
Usage (f3, .venv): PYTHONPATH=. .venv/bin/python eval/stress_check.py <model.onnx> ...
"""
import json
import os
import re
import sys

import numpy as np
import onnx
import onnxruntime as ort
from piper import PiperVoice

from respell import ru_phonemes

VOWELS = set('aɑʌəoɔuʊiɪyɨeɛæɐ')
TEXTS = json.load(open('/root/st-m1/eval/texts.json', encoding='utf-8')) + [
    'Не склоняясь ни к одной из этих крайностей, Татхагата пробудился в срединный путь, который способствует видению.',
    'Каков будет его будущий удел? Каково его будущее направление?',
    'Поскольку он считает всё это таковым, он не волнуется о том, чего не существует.',
    'Таково пятое знание, обретённое им, благородное, сверхмирское, которого не имеют обычные заурядные люди.',
    '«Точно так же, Маханама, благородный ученик, наделённый этими четырьмя вещами, склоняется к ниббане».',
    'Он увидел некую женщину в родовых муках, с болезненными родами, от дома к дому.']


def session(model):
    align = model.replace('.onnx', '.align.onnx')
    if not os.path.exists(align):
        m = onnx.load(model)
        m.graph.output.append(onnx.helper.make_tensor_value_info('/Ceil_output_0', onnx.TensorProto.FLOAT, None))
        onnx.save(m, align)
    return ort.InferenceSession(align, providers=['CPUExecutionProvider'])


def check(model):
    voice = PiperVoice.load(model, config_path=model + '.json')
    sess, bad, words = session(model), [], 0
    for text in TEXTS:
        for ph in ru_phonemes(voice, text):
            ids = voice.phonemes_to_ids(ph)  # ^ _ p1 _ p2 _ ... $: phoneme k at 2 + 2k
            _, dur = sess.run(None, {'input': np.array([ids], dtype=np.int64), 'input_lengths': np.array([len(ids)], dtype=np.int64),
                                     'scales': np.array([0, 4, 0], dtype=np.float32)})
            dur = dur.reshape(-1)
            word, stress_next = [], False  # word: (phoneme, duration incl. its pad, stressed)
            for k, p in enumerate(ph + [' ']):
                if p == ' ' or not (p.isalpha() or p in 'ˈʲː'):
                    v = [w for w in word if w[0] in VOWELS]
                    if len(v) > 1 and sum(s for *_, s in v) == 1:
                        words += 1
                        if max(v, key=lambda w: w[1])[2] is False:
                            bad.append(''.join(w[0] if not w[2] else 'ˈ' + w[0] for w in word))
                    word = []
                    continue
                d = float(dur[2 + 2 * k] + dur[3 + 2 * k])
                if p == 'ˈ':  # the mark gets frames of its own: they belong to its vowel
                    stress_next, carry = True, d
                    continue
                stressed = p in VOWELS and stress_next
                stress_next = stress_next and not stressed
                word.append((p, d + (carry if stressed else 0), stressed))
    return words, bad


if __name__ == '__main__':
    for model in sys.argv[1:]:
        n, bad = check(model)
        print(f'{model}: {len(bad)} of {n} words ({len(bad) / n:.1%}) longest vowel not the stressed one')
        print('   ', ' '.join(bad[:40]))
