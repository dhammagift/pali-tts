"""Forced alignment of Pali recordings against SuttaCentral root text (torchaudio MMS_FA).

align(wav_path, segments) -> list of words {seg, word, start, end, score}, in reading order.
A star token between segments absorbs audio that is not in the text (headings, coughs, pauses).
Heavy (300M-param model): run it in CI, not on the production server.
"""
import re
import subprocess
import unicodedata

import numpy as np
import torch
import torchaudio

SR = 16000
CHUNK = 20 * SR  # wav2vec2 attention is quadratic: feed 20 s windows
BUNDLE = torchaudio.pipelines.MMS_FA
_model = None


def model():
    global _model
    if _model is None:
        _model = BUNDLE.get_model(with_star=True).eval()
    return _model


def load(path, sr=SR):
    pcm = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def emission(wav):
    wav = torch.from_numpy(wav.copy())
    out = []
    with torch.inference_mode():
        for i in range(0, len(wav), CHUNK):
            chunk = wav[i:i + CHUNK]
            if len(chunk) < SR // 10:
                break
            out.append(model()(chunk.unsqueeze(0))[0][0])
    return torch.cat(out)


def romanize(word):
    """IAST word -> the a-z alphabet MMS_FA knows (diacritics dropped)."""
    t = unicodedata.normalize('NFD', word.lower())
    return re.sub(r'[^a-z]', '', ''.join(c for c in t if not unicodedata.combining(c)))


def align(path, segments):
    """segments: list of (key, text). Words keep their original IAST spelling and punctuation."""
    wav = load(path)
    em = emission(wav)
    sec_per_frame = len(wav) / SR / em.shape[0]
    words, meta = ['*'], [None]
    for si, (_, text) in enumerate(segments):
        for w in text.split():
            r = romanize(w)
            if r:
                words.append(r)
                meta.append((si, w))
        words.append('*')
        meta.append(None)
    spans = BUNDLE.get_aligner()(em, BUNDLE.get_tokenizer()(words))
    out = []
    for sp, m in zip(spans, meta):
        if m is None:
            continue
        out.append({'seg': segments[m[0]][0], 'word': m[1],
                    'start': round(sp[0].start * sec_per_frame, 3), 'end': round(sp[-1].end * sec_per_frame, 3),
                    'score': round(float(np.mean([c.score for c in sp])), 3)})
    return out
