"""Step 2 of 2 (f3, /root/venv-ml): every student's 40 lines scored without ears.
- CER: whisper-small (ru) transcript against the text, lower case, no punctuation, ё = е. Lower = clearer.
- likeness: cosine of WavLM speaker vectors (microsoft/wavlm-base-plus-sv) to the mean of 40 teacher clips (the
  Supertonic M1 training data). Higher = closer to M1.
Prints a table; /root/st-m1/eval/scores.json.
"""
import glob
import json
import re

import librosa
import numpy as np
import torch
from transformers import AutoFeatureExtractor, WavLMForXVector, pipeline

torch.set_num_threads(2)
E = '/root/st-m1/eval'
texts = json.load(open(f'{E}/texts.json', encoding='utf-8'))
norm = lambda s: re.sub(r'\s+', ' ', re.sub(r'[^а-я ]', ' ', s.lower().replace('ё', 'е'))).strip()


def cer(ref, hyp):
    a, b = norm(ref), norm(hyp)
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x != y))
    return d[-1] / max(1, len(a))


asr = pipeline('automatic-speech-recognition', model='openai/whisper-small', device='cpu')
fe = AutoFeatureExtractor.from_pretrained('microsoft/wavlm-base-plus-sv')
sv = WavLMForXVector.from_pretrained('microsoft/wavlm-base-plus-sv').eval()


def emb(paths):
    out = []
    for p in paths:
        y, _ = librosa.load(p, sr=16000)
        with torch.no_grad():
            e = sv(**fe(y, sampling_rate=16000, return_tensors='pt')).embeddings[0]
        out.append(torch.nn.functional.normalize(e, dim=-1).numpy())
    return np.array(out)


teacher = emb(sorted(glob.glob('/root/st-m1/data/wavs/*.wav'))[:40]).mean(0)
teacher /= np.linalg.norm(teacher)
scores = {}
for d in sorted(glob.glob(f'{E}/*/')):
    base = d.rstrip('/').split('/')[-1]
    wavs = sorted(glob.glob(d + '*.wav'))
    hyps = [asr(librosa.load(w, sr=16000)[0], generate_kwargs={'language': 'russian', 'task': 'transcribe'})['text'] for w in wavs]
    c = [cer(t, h) for t, h in zip(texts, hyps)]
    like = float((emb(wavs) @ teacher).mean())
    scores[base] = {'cer': float(np.mean(c)), 'like': like, 'worst': sorted(zip(c, texts, hyps), reverse=True)[:3]}
    print(f'{base:8} CER {np.mean(c):.3f}  likeness {like:.3f}', flush=True)
json.dump(scores, open(f'{E}/scores.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
