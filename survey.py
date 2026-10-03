"""Survey the owner's human recordings before choosing training data.

Per file: duration, noise floor, speech level, SNR (speech - noise, dB), clipping share.
Usage: python survey.py out/survey  -> out/survey/survey.json
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

import numpy as np

REPO = 'https://raw.githubusercontent.com/dhammagift/audio/HEAD/'
TREE = 'https://api.github.com/repos/dhammagift/audio/git/trees/HEAD?recursive=1'
SR = 16000


def candidates():
    """Human recordings only: Patimokkha (chapters, rules, -old), DN22 fragments, *_jiv suttas."""
    paths = [x['path'] for x in json.load(urllib.request.urlopen(TREE))['tree'] if x['path'].endswith('.mp3')]
    keep = []
    for p in paths:
        name = os.path.basename(p)
        if p.startswith(('bu-pm/', 'bi-pm/')):
            keep.append(p)
        elif p.startswith('dn/dn2.9/') or '_jiv' in name:
            keep.append(p)
    return sorted(keep)


def stats(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    frames = x[:len(x) // 800 * 800].reshape(-1, 800)  # 50 ms
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    noise, speech = np.percentile(db, 10), np.percentile(db, 90)
    return {'dur': round(len(x) / SR, 1), 'noise_db': round(float(noise), 1), 'speech_db': round(float(speech), 1),
            'snr_db': round(float(speech - noise), 1), 'clip_pct': round(float((np.abs(x) > 0.99).mean() * 100), 3)}


def main(out):
    os.makedirs(out, exist_ok=True)
    res = []
    for p in candidates():
        local = f'cache/audio/{p}'
        if not os.path.exists(local):
            os.makedirs(os.path.dirname(local), exist_ok=True)
            urllib.request.urlretrieve(REPO + p, local)
        s = stats(local)
        res.append({'path': p, **s})
        print(p, s, flush=True)
    json.dump(res, open(f'{out}/survey.json', 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
