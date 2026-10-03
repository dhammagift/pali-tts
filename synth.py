"""Render every case in cases.tsv with Piper hi_IN voices, fed with our Pali IPA (no espeak).

Usage: .venv/bin/python synth.py  -> out/<id>.<variant>.mp3, out/index.json
"""
import json
import subprocess
import time
import wave

from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa

LENGTH = 1.15  # slightly slower than Hindi default: Pali recitation pace
VARIANTS = [  # (variant id, voice, how phonemes are made)
    ('rohan.ipa_stress', 'rohan', 'ipa_stress'),
    ('rohan.full_a', 'rohan', 'full_a'),
    ('rohan.full_a_stress', 'rohan', 'full_a_stress'),
    ('pratham.full_a_stress', 'pratham', 'full_a_stress'),
    ('priyamvada.full_a_stress', 'priyamvada', 'full_a_stress'),
]

cases = [l.rstrip('\n').split('\t') for l in open('cases.tsv', encoding='utf-8')][1:]
dev = json.load(open('out/devanagari.json', encoding='utf-8'))
voices = {v: PiperVoice.load(f'models/hi_IN-{v}-medium.onnx') for v in {x[1] for x in VARIANTS}}
cfg = SynthesisConfig(length_scale=LENGTH, noise_scale=0.6, noise_w_scale=0.7)
index, rtf = {}, []

for cid, text, note in cases:
    ipa = {'ipa_stress': to_ipa(text), 'full_a': to_ipa(text, stress=False, full_a=True),
           'full_a_stress': to_ipa(text, full_a=True)}
    index[cid] = {'text': text, 'note': note, 'ipa': ipa['ipa_stress'], 'devanagari': dev[cid]['google']}
    for vid, vname, mode in VARIANTS:
        voice = voices[vname]
        if mode == 'espeak':  # stock Piper: our Devanagari through espeak-ng Hindi rules
            sentences = voice.phonemize(dev[cid]['devanagari'])
        else:
            sentences = [list(ipa[mode])]
        t0 = time.time()
        audio = b''.join(voice.phoneme_ids_to_audio(voice.phonemes_to_ids(s), cfg).tobytes()
                         for s in sentences if s)
        wav = f'out/{cid}.{vid}.wav'
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(voice.config.sample_rate)
            w.writeframes((__import__('numpy').frombuffer(audio, dtype='float32') * 32767).astype('int16').tobytes())
        secs = len(audio) / 4 / voice.config.sample_rate
        rtf.append((time.time() - t0) / max(secs, 0.01))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-b:a', '64k', wav[:-3] + 'mp3'], check=True)
    print(cid, ipa['ipa_stress'][:70])

json.dump({'variants': [v[0] for v in VARIANTS], 'cases': index,
           'rtf': round(sum(rtf) / len(rtf), 3)}, open('out/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('mean RTF', round(sum(rtf) / len(rtf), 3))
