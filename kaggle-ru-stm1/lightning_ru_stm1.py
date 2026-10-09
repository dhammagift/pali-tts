"""Run kaggle-ru-stm1/train.py on Lightning AI (free tier: one studio, up to 80 GPU h; a free studio turns paid after
4 h, so every run starts the studio, trains 2:30 and stops it). One run per base voice, in order, outputs to
/root/st-m1/runs/<base>/ on f3. A smoke run (8 min) first proves the environment.
Usage (f3): set -a; . /root/.secrets/lightning; set +a
  uvx --python 3.12 --with lightning-sdk python kaggle-ru-stm1/lightning_ru_stm1.py /root/st-m1/data.zip ruslan denis dmitri
"""
import os
import sys
import time

from lightning_sdk import Machine, Studio
from lightning_sdk.utils.resolve import _get_authed_user

HOME = '/teamspace/studios/this_studio'
DATA_ZIP, BASES = sys.argv[1], sys.argv[2:]
LOCAL = '/root/st-m1/runs'
HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = Studio(name='ru-stm1', teamspace='general', user=_get_authed_user().name, create_ok=True)


def run(base, smoke=False):
    """Start the studio, train one base, fetch its outputs, stop the studio (always: the 4 h rule)."""
    work = f'{HOME}/work-{base}{"-smoke" if smoke else ""}'
    print(time.strftime('%H:%M'), 'start', base, 'smoke' if smoke else '', flush=True)
    STUDIO.start(Machine.T4)
    try:
        STUDIO.upload_file(f'{HERE}/train.py', f'{HOME}/train.py')
        if 'ok' not in STUDIO.run(f'test -f {HOME}/input/metadata.csv && echo ok || echo missing'):
            STUDIO.upload_file(DATA_ZIP, f'{HOME}/data.zip')
            STUDIO.run(f'mkdir -p {HOME}/input && cd {HOME}/input && python -m zipfile -e ../data.zip . && rm ../data.zip')
        env = f'INPUT={HOME}/input WORK={work} BASE={base} SMOKE={int(smoke)}'
        STUDIO.run(f'rm -rf {work} && mkdir -p {work} && cd {HOME} && (nohup env {env} python train.py > {work}/log.txt 2>&1 &)')
        while True:
            time.sleep(300)
            state = STUDIO.run(f'tail -c 300 {work}/log.txt | grep -q "^done" && echo done || '
                               f'(pgrep -f "python train.py" > /dev/null && echo running || echo dead)').strip()
            print(time.strftime('%H:%M'), base, state, flush=True)
            if state != 'running':
                break
        out = f'{LOCAL}/{base}{"-smoke" if smoke else ""}'
        os.makedirs(out, exist_ok=True)
        files = STUDIO.run(f'ls {work}/out 2>/dev/null; true').split()
        STUDIO.download_file(f'{work}/log.txt', f'{out}/log.txt')
        for f in sorted(set(files)):
            if f.endswith(('.onnx', '.json', '.wav')) or (f == 'last.ckpt' and not smoke):
                STUDIO.download_file(f'{work}/out/{f}', f'{out}/{f}')
        if STUDIO.run(f'test -f {work}/error.txt && echo yes; true').strip() == 'yes':
            STUDIO.download_file(f'{work}/error.txt', f'{out}/error.txt')
        return state == 'done'
    finally:
        STUDIO.stop()
        print(time.strftime('%H:%M'), 'stopped', flush=True)


if __name__ == '__main__':
    if not run(BASES[0], smoke=True):
        sys.exit('smoke run failed: see /root/st-m1/runs/*-smoke/')
    for b in BASES:
        run(b)
