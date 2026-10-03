"""Build a Piper fine-tuning dataset from the owner's Pali recordings (runs in GitHub Actions).

For each manifest item: download mp3 (dhammagift/audio) + root text (suttacentral/sc-data), denoise
(DeepFilterNet), align words to audio, cut 1-15 s clips at punctuation/segment boundaries.

Usage: python prepare.py dataset/test.json out/ds
Output: out/ds/review/<item>/<n>.{raw,dn}.mp3 (listening check), out/ds/train/wavs/*.wav (22.05 kHz,
denoised), out/ds/clips.json (text, IPA, times, alignment score).
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

from align import align
from pali_ipa import to_ipa

AUDIO_URL = 'https://raw.githubusercontent.com/dhammagift/audio/HEAD/'
TEXT_URL = 'https://raw.githubusercontent.com/suttacentral/sc-data/main/sc_bilara_data/root/pli/ms/'
TITLE_KEY = re.compile(r':(\d+\.)*0(\.\d+)?$')  # x:0.1, x:66.0.2 — titles/headings, often English
MIN_CUT, MAX_CLIP, MIN_CLIP = 3.0, 14.0, 1.0
PAD_IN, PAD_OUT = 0.2, 0.3


def fetch(url, path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(url, path)
    return path


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *args], check=True)


def clips_from_words(words):
    """Greedy cut: close a clip at a punctuation or segment boundary once it is >= MIN_CUT s,
    or at any word boundary before it would exceed MAX_CLIP s."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        dur = w['end'] - cur[0]['start']
        boundary = nxt is None or nxt['seg'] != w['seg'] or re.search(r'[,.;:?!—’”]$', w['word'])
        too_long = nxt is not None and nxt['end'] - cur[0]['start'] > MAX_CLIP
        if (boundary and dur >= MIN_CUT) or too_long or nxt is None:
            out.append(cur)
            cur = []
    return out


def main(manifest, outdir):
    items = json.load(open(manifest))
    os.makedirs(f'{outdir}/train/wavs', exist_ok=True)
    clips = []
    for it in items:
        mp3 = fetch(AUDIO_URL + it['audio'], f'cache/audio/{it["audio"]}')
        root = json.load(open(fetch(TEXT_URL + it['text'], f'cache/text/{it["text"]}'), encoding='utf-8'))
        lo, hi = it.get('range', (0, 10 ** 6))  # top-level section numbers, e.g. pm:65..75 = Pācittiya chapter 1
        segs = [(k, v) for k, v in root.items()
                if v.strip() and not TITLE_KEY.search(k) and re.search(it.get('keys', ''), k)
                and lo <= int(k.split(':')[1].split('.')[0]) <= hi]
        raw = f'cache/wav/{it["id"]}.wav'
        os.makedirs('cache/wav/dn', exist_ok=True)
        ffmpeg('-i', mp3, '-ac', '1', '-ar', '48000', raw)  # DeepFilterNet wants 48 kHz
        subprocess.run(['./deep-filter', '--output-dir', 'cache/wav/dn', raw], check=True, capture_output=True)
        dn = f'cache/wav/dn/{it["id"]}.wav'
        words = align(dn, segs)
        os.makedirs(f'{outdir}/review/{it["id"]}', exist_ok=True)
        groups = clips_from_words(words)
        for n, g in enumerate(groups):
            prev_end = groups[n - 1][-1]['end'] if n else 0
            next_start = groups[n + 1][0]['start'] if n + 1 < len(groups) else g[-1]['end'] + PAD_OUT
            start = max(g[0]['start'] - PAD_IN, (prev_end + g[0]['start']) / 2)
            end = min(g[-1]['end'] + PAD_OUT, (g[-1]['end'] + next_start) / 2)
            if end - start < MIN_CLIP:
                continue
            name = f'{it["id"]}_{n:03d}'
            text = re.sub(r'[“”‘’"]', '', ' '.join(w['word'] for w in g)).strip()
            cut = ['-ss', f'{start:.3f}', '-to', f'{end:.3f}']
            for src, kind in ((raw, 'raw'), (dn, 'dn')):
                ffmpeg(*cut, '-i', src, '-ac', '1', '-ar', '22050', '-b:a', '64k', f'{outdir}/review/{it["id"]}/{n:03d}.{kind}.mp3')
            ffmpeg(*cut, '-i', dn, '-ac', '1', '-ar', '22050', '-sample_fmt', 's16', f'{outdir}/train/wavs/{name}.wav')
            scores = [w['score'] for w in g]
            clips.append({'item': it['id'], 'n': n, 'name': name, 'text': text, 'ipa': to_ipa(text, full_a=True),
                          'keys': sorted({w['seg'] for w in g}), 'start': round(start, 2), 'end': round(end, 2),
                          'dur': round(end - start, 2), 'score': round(sum(scores) / len(scores), 3),
                          'min_score': min(scores)})
        print(it['id'], len(segs), 'segments,', len(groups), 'clips', flush=True)
    json.dump(clips, open(f'{outdir}/clips.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('total', len(clips), 'clips', round(sum(c['dur'] for c in clips) / 60, 1), 'min')


if __name__ == '__main__':
    main(*sys.argv[1:3])
