"""Kaggle CPU job: data for pratham with Google's pronunciation (owner 2026-11-16, round gsa1).
1. kNN-VC (bshall/knn-vc, MIT) turns Google's Sanskrit TTS readings (dataset gsa-google, gtts/ in GitHub Actions) into
   pratham's timbre (matching set: pratham's own readings, gsa-texts/ref), 0.1 s before and 0.15 s after (as Piper ends);
2. the phoneme recogniser (wav2vec2-lv-60-espeak-cv-ft) hears each converted clip; scores.tsv compares it with the ids
   the voice will be trained on (a coarse skeleton: voicing, aspiration, length, retroflex merged), whole and last
   quarter, so cut or garbled clips can be left out before training.
Out: gsa-data.tar (data/wavs, data/metadata.csv, data/phonemes.json) and scores.tsv. SMOKE file in an input: 12 clips.
"""
import difflib
import glob
import itertools
import json
import os
import re
import subprocess

import soundfile as sf
import torch
import torchaudio

torch.set_num_threads(os.cpu_count())
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'  # GPU when given (owner 2026-11-16: finish today), else CPU
INPUT, W = '/kaggle/input', '/kaggle/working'
T = os.path.dirname(glob.glob(f'{INPUT}/**/texts.csv', recursive=True)[0])
# Google's readings come as tars (one file uploads to Kaggle in minutes, 2400 wavs took hours): unpacked here
for tar in glob.glob(f'{INPUT}/**/gsa-google*.tar', recursive=True):
    subprocess.run(f'mkdir -p {W}/src && tar -xf {tar} -C {W}/src', shell=True, check=True)
SRC = {os.path.basename(f): f for f in glob.glob(f'{INPUT}/**/s[0-9]*.wav', recursive=True) + glob.glob(f'{W}/src/s[0-9]*.wav')}
SMOKE = bool(glob.glob(f'{INPUT}/**/SMOKE', recursive=True))
DATA = f'{W}/data'
inv = {i: p for p, ids in json.load(open(f'{T}/phonemes.json', encoding='utf-8')).items() for i in ids}
rows = [r.split('|') for r in open(f'{T}/texts.csv', encoding='utf-8').read().split('\n') if r]
# a line Google gave up on is an empty file or one with a zeroed header (3 of 2400 in the first run): left out
rows = [r for r in rows if r[0] in SRC and open(SRC[r[0]], 'rb').read(4) == b'RIFF'][:12 if SMOKE else None]
# one of N CPU kernels (gsa-data-b<k>, while the GPUs are queued): every N-th clip; 'all' for one kernel
PART, PARTS = 'all', 1
rows = rows[int(PART)::PARTS] if PART != 'all' else rows
NAME = 'gsa-data' if PART == 'all' else f'gsa-data-b{PART}'
print('clips', len(rows), 'of', len(SRC), flush=True)

knn = torch.hub.load('bshall/knn-vc', 'knn_vc', trust_repo=True, prematched=True, pretrained=True, device=DEV)


def wav16(f):  # tensors, not paths: knn-vc's own torchaudio.load needs torchcodec in new torchaudio
    w, s = sf.read(f, dtype='float32')
    return torchaudio.functional.resample(torch.from_numpy(w), s, 16000)[None]


matching = knn.get_matching_set([wav16(f) for f in sorted(glob.glob(f'{T}/ref/*.wav'))], vad_trigger_level=0)

from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402

M = 'facebook/wav2vec2-lv-60-espeak-cv-ft'
fe, rec = Wav2Vec2FeatureExtractor.from_pretrained(M), Wav2Vec2ForCTC.from_pretrained(M).eval().to(DEV)
vocab = {v: k for k, v in json.load(open(hf_hub_download(M, 'vocab.json'))).items()}
SKEL = [('dʒ', 'c'), ('tʃ', 'c'), ('ɟ', 'c'), *[(a, 'a') for a in 'ʌɐəɑæ'], *[(a, 'i') for a in 'ɪɨ'], *[(a, 'u') for a in 'ʊʉ'],
        ('ɛ', 'e'), ('ɔ', 'o'), ('b', 'p'), ('d', 't'), ('ɖ', 't'), ('ʈ', 't'), ('ɡ', 'k'), ('g', 'k'), ('ɲ', 'n'), ('ɳ', 'n'),
        ('ŋ', 'n'), ('ʋ', 'v'), ('w', 'v'), ('ɾ', 'r'), ('ɹ', 'r'), ('ɭ', 'l'), ('ʂ', 's'), ('ʃ', 's'), ('ɕ', 's')]


def skel(s):  # a coarse phoneme skeleton both strings can agree on
    s = re.sub('[ˈˌːʰʲ̃ ̃,.;:!?—-]', '', s)
    for a, b in SKEL:
        s = s.replace(a, b)
    return ''.join(k for k, _ in itertools.groupby(s.replace('h', '')))


def heard(a16):
    with torch.no_grad():
        ids = rec(fe(a16, sampling_rate=16000, return_tensors='pt').input_values.to(DEV)).logits.argmax(-1)[0].tolist()
    return ''.join(vocab[i] for i, _ in itertools.groupby(ids) if vocab[i] not in ('<pad>', '<s>', '</s>'))


os.makedirs(f'{DATA}/wavs', exist_ok=True)
meta, scores = [], ['name\twhole\ttail\theard\twant']
for k, (name, deva, ids) in enumerate(rows):
    try:
        out = knn.match(knn.get_features(wav16(SRC[name]).to(DEV)), matching, topk=8).cpu()
    except RuntimeError as e:  # a clip too short for knn-vc's loudness gate (part b2 died on one): left out
        print('skip', name, e, flush=True)
        continue
    h = heard(out.numpy())
    want = ''.join(inv[int(i)] for i in ids.split() if int(i) > 3)
    a, b = skel(h), skel(want)
    q = max(4, len(b) // 4)
    whole = difflib.SequenceMatcher(None, a, b).ratio()
    tail = difflib.SequenceMatcher(None, a[-q:], b[-q:]).ratio()
    scores.append(f'{name}\t{whole:.3f}\t{tail:.3f}\t{h}\t{want}')
    out = torch.cat([torch.zeros(1600), out, torch.zeros(2400)])  # 0.1 s before, 0.15 s after, as Piper voices end
    sf.write(f'{DATA}/wavs/{name}', torchaudio.functional.resample(out, 16000, 22050).numpy(), 22050, subtype='PCM_16')
    meta.append(f'{name}|{deva}|{ids}')
    if k % 100 == 0:
        print(k, name, f'{whole:.2f} {tail:.2f}', flush=True)
open(f'{DATA}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(meta) + '\n')
open(f'{W}/{NAME}-scores.tsv' if PART != 'all' else f'{W}/scores.tsv', 'w', encoding='utf-8').write('\n'.join(scores) + '\n')
subprocess.run(f'cp {T}/phonemes.json {DATA}/ && tar -cf {W}/{NAME}.tar -C {W} data && rm -rf {DATA} {W}/src', shell=True, check=True)
print('done', len(meta), flush=True)
