"""Run the ears (kaggle-ears) on rounds: packs their clips + what each was asked to say into a NEW Kaggle dataset
(one dataset per run keeps runs apart), points the kernel at it, runs it, downloads
heard.json and scores it with ears.py.
Usage: python3 ears_kaggle.py r28 [es7 ...]  -> out/ears/scored.json (and a short report on stdout)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from ears import score
from pali_ipa import to_ipa

K = ['/root/.local/bin/uvx', '--python', '3.12', 'kaggle@2.2.4']
ENV = dict(os.environ, KAGGLE_API_TOKEN=open('/root/.secrets/kaggle').read().strip())


def kaggle(*a):
    return subprocess.run(K + list(a), env=ENV, capture_output=True, text=True).stdout


def pack(rounds, d, slug):
    os.makedirs(f'{d}/audio')
    man = []
    for r in rounds:
        idx = json.load(open(f'out/{r}/index.json', encoding='utf-8'))
        for s in idx.get('sections', [idx]):
            for ph in s['phrases']:
                for v in ph['variants']:
                    src = os.path.normpath(f'out/{r}/{v["file"]}')
                    dst = f'{r}__{v["file"].replace("../", "").replace("/", "_")}'
                    shutil.copy(src, f'{d}/audio/{dst}')
                    man.append({'round': r, 'phrase': ph['id'], 'variant': v['id'], 'text': ph['text'], 'file': dst,
                                'expected': v.get('sent') or ph.get('ipa') or to_ipa(ph['text'], full_a=True)})
    json.dump(man, open(f'{d}/manifest.json', 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump({'title': slug, 'id': f'dhammagift/{slug}', 'licenses': [{'name': 'CC-BY-NC-SA-4.0'}]},
              open(f'{d}/dataset-metadata.json', 'w'))
    return len(man)


if __name__ == '__main__':
    rounds = sys.argv[1:]
    slug = f"pali-tts-ears-{'-'.join(rounds)}-{int(time.time())}"[:50]
    with tempfile.TemporaryDirectory() as d:
        print(pack(rounds, d, slug), 'clips', flush=True)
        print(kaggle('datasets', 'create', '-p', d, '--dir-mode', 'zip').strip()[-120:], flush=True)
    for _ in range(40):
        if 'ready' in kaggle('datasets', 'status', f'dhammagift/{slug}'):
            break
        time.sleep(15)
    meta = json.load(open('kaggle-ears/kernel-metadata.json'))
    meta['dataset_sources'] = [f'dhammagift/{slug}']
    json.dump(meta, open('kaggle-ears/kernel-metadata.json', 'w'), indent=1)
    print(kaggle('kernels', 'push', '-p', 'kaggle-ears').strip()[-120:], flush=True)
    for _ in range(40):  # right after a push the status still shows the previous run as COMPLETE
        if 'COMPLETE' not in kaggle('kernels', 'status', 'dhammagift/pali-tts-ears'):
            break
        time.sleep(15)
    while not any(x in kaggle('kernels', 'status', 'dhammagift/pali-tts-ears') for x in ('COMPLETE', 'ERROR', 'CANCEL')):
        time.sleep(30)
    os.makedirs('out/ears', exist_ok=True)
    if os.path.exists('out/ears/heard.json'):
        os.remove('out/ears/heard.json')  # the CLI does not overwrite an existing file: the old one looked like a stale run
    kaggle('kernels', 'output', 'dhammagift/pali-tts-ears', '-p', 'out/ears', '-o')
    heard = json.load(open('out/ears/heard.json', encoding='utf-8'))
    assert {h['round'] for h in heard} == set(rounds), 'heard.json is not from this run'
    for h in heard:
        h.update(score(h['expected'], h['heard']))
    json.dump(heard, open('out/ears/scored.json', 'w', encoding='utf-8'), ensure_ascii=False)
    for h in heard:
        print(f"{h['round']} {h['phrase']:8} {h['variant']:5} err {h['err']:.2f} {h['diff'][:40]:40} | {h['heard'][:70]}")
