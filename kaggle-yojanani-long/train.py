"""Kaggle GPU job, the long run (owner 2026-10-26: at least 100 epochs in all; the 1 h run read 34 of 36 short words
right, the model in DG 13): from yojanani-short-train's last.ckpt (28 + 8 epochs), 8 h more, ~64 epochs. Otherwise as there:
Yojanāni (Miles's ElevenLabs voice, miles2: 2250 sentences, from en_US-kusal, 28 epochs, the model in
DG on 2026-10-25) further trained with 699 short lines and single words in the same voice (make_en_miles_short.py),
each 3 times: it read a word alone badly ("monks" as "next"), it had never heard one.
Weights from yojanani-voice-data/last.ckpt (warmstart: a fresh optimizer and timer, so MAX_TIME is this run's own).
"""
import glob
import os
import re
import subprocess
import sys

MAX_TIME = '00:08:00:00'  # smoke run: 00:00:04:00 (~0.5 epoch of 488 steps, ~8 min each on a T4)
REPEAT = 3
W, INPUT, NAME = '/kaggle/working', '/kaggle/input', 'en_yojanani_short'


def cleanup():
    subprocess.run(f'rm -rf {W}/cache {W}/piper1-gpl {W}/wavs', shell=True)


def sh(cmd):
    print('+', cmd, flush=True)
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout[-20000:], flush=True)
    if r.returncode:
        open(f'{W}/error.txt', 'w').write(f'$ {cmd}\n\n{r.stdout[-15000:]}')
        cleanup()
        sys.exit(r.returncode)


try:
    find = lambda pat: sorted(glob.glob(f'{INPUT}/**/{pat}', recursive=True))
    # the long run starts from the short run's output (kernel source), not from yojanani-voice-data's
    CKPT = [c for c in find('last.ckpt') if 'yojanani-short-train' in c][0]  # no silent fallback to the 28-epoch one
    LONG, SHORT = find('metadata_kusal.csv')[0], find('metadata_short.csv')[0]
    os.makedirs(f'{W}/wavs', exist_ok=True)
    for z in find('wavs.zip'):
        sh(f'unzip -q -o {z} -d {W}/unz')
    for f in find('*.wav') + glob.glob(f'{W}/unz/**/*.wav', recursive=True):  # both datasets' clips in one dir
        os.symlink(f, f'{W}/wavs/{os.path.basename(f)}') if not os.path.exists(f'{W}/wavs/{os.path.basename(f)}') else None
    long, short = open(LONG, encoding='utf-8').read().splitlines(), open(SHORT, encoding='utf-8').read().splitlines()
    have = {os.path.basename(f)[:-4] for f in os.listdir(f'{W}/wavs')}
    missing = [r.split('|')[0] for r in long + short if r.split('|')[0] not in have]
    if missing:
        raise SystemExit(f'{len(missing)} clips without a wav, e.g. {missing[:5]}')
    # the trainer keys its cache by clip name, so a repeat is a symlink of its own
    rows = list(long)
    for k in range(REPEAT):
        for r in short:
            name, rest = r.split('|', 1)
            dup = f'{name}_{k}'
            os.symlink(f'{W}/wavs/{name}.wav', f'{W}/wavs/{dup}.wav') if not os.path.exists(f'{W}/wavs/{dup}.wav') else None
            rows.append(f'{dup}|{rest}')
    open(f'{W}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    print(len(long), 'long +', len(short), 'short x', REPEAT, '=', len(rows), 'rows; ckpt', CKPT, flush=True)

    sh('nvidia-smi --query-gpu=name,memory.total --format=csv')
    sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
    os.chdir(f'{W}/piper1-gpl')
    sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
    main_py = 'src/piper/train/__main__.py'
    src = open(main_py).read()  # read before open(..., 'w') empties it
    open(main_py, 'w').write(re.sub(r'\n\s*ModelCheckpoint\(\s*monitor="val_mos".*?\),(?=\n)', '', src, flags=re.S))
    sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript -e '.[train]'")
    sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
    phonemes = find('phonemes_kusal.json')[0]
    os.makedirs(f'{W}/out', exist_ok=True)
    sh(' '.join([
        'python -m piper.train fit', f'--data.voice_name {NAME}', f'--data.csv_path {W}/metadata.csv',
        f'--data.audio_dir {W}/wavs', '--model.sample_rate 22050', '--data.espeak_voice en-us', f'--data.cache_dir {W}/cache',
        f'--data.config_path {W}/out/{NAME}.onnx.json', '--data.batch_size 8', '--data.num_workers 2',
        '--data.dataset_type phoneme_ids', '--data.num_symbols 256', f'--data.phonemes_path {phonemes}',
        f'--model.warmstart_ckpt {CKPT}', '--trainer.max_epochs 3000', f'--trainer.max_time {MAX_TIME}',
        '--trainer.accelerator gpu --trainer.devices 1', '--trainer.check_val_every_n_epoch 50', f'--trainer.default_root_dir {W}/train',
    ]))
    last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))
    if not last:
        raise SystemExit('training wrote no last.ckpt')
    last = last[-1]
    sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/{NAME}.onnx')
    sh(f'cp {last} {W}/out/last.ckpt')
finally:
    cleanup()
    subprocess.run(f'rm -rf {W}/unz', shell=True)
print('done')
