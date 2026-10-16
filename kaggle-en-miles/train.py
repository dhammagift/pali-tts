"""Kaggle GPU job: fine-tune Piper (VITS, medium) from en_US-ryan on Miles's own readings of the record-en script
(dataset en-miles-voice-data: make_en_miles_dataset.py; demo on the first 100 lines, ~8.5 min, owner 2026-10-16).
Copy of kaggle-ru-stm1/train.py; export ONNX, render samples. Phoneme ids are what tts_server gives an English voice
(respell.en_phonemes). SMOKE=1 runs a few minutes to validate the environment.
"""
import glob
import os
import re
import subprocess
import sys

SMOKE = os.environ.get('SMOKE', '0') == '1' or bool(glob.glob(f"{os.environ.get('INPUT', '/kaggle/input')}/**/SMOKE", recursive=True))
# RESUME: a previous run's last.ckpt in the inputs (a dataset with last.ckpt) - training continues from it
# (optimizer, epoch counter) instead of a fresh warm start from ryan
INPUT = os.environ.get('INPUT', '/kaggle/input')
RESUME = os.environ.get('RESUME') or (glob.glob(f'{INPUT}/**/last.ckpt', recursive=True) or [None])[0]  # Kaggle flattens the dataset: at its root
# 100 clips, ~8.5 min: 2 h is plenty for a demo
MAX_TIME = '00:00:08:00' if SMOKE else os.environ.get('MAX_TIME', '00:02:00:00')
W = os.environ.get('WORK', '/kaggle/working')
DATA = os.path.dirname(glob.glob(f'{INPUT}/**/metadata.csv', recursive=True)[0])
CKPT_URL = 'https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/en/en_US/ryan/medium/epoch%3D4641-step%3D3104302.ckpt'
SAMPLES = [
    'So I have heard. At one time the Buddha was staying near Sāvatthī in Jeta’s Grove, Anāthapiṇḍika’s monastery.',
    'There the Buddha addressed the mendicants, “Mendicants!”',
    'And what, mendicants, is suffering? Rebirth is suffering, old age is suffering, death is suffering.',
    'Tathāgata, nibbāna, Dhamma, Saṅgha.',
]


def sh(cmd):
    """Run a step; on failure keep its output tail in error.txt (the Kaggle log API is hard to reach)."""
    print('+', cmd, flush=True)
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout[-20000:], flush=True)
    if r.returncode:
        open(f'{W}/error.txt', 'w').write(f'$ {cmd}\n\n{r.stdout[-15000:]}')
        cleanup()
        sys.exit(r.returncode)


def cleanup():
    # thousands of cache files make the kernel output listing hit Kaggle's API rate limit
    subprocess.run(f'rm -rf {W}/cache {W}/base.ckpt {W}/piper1-gpl', shell=True)


sh('nvidia-smi --query-gpu=name,memory.total --format=csv')
if not os.path.exists(f'{W}/piper1-gpl'):
    sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
# legacy TorchScript exporter: torch >= 2.9 defaults to dynamo, which cannot trace VITS (run v4 died there)
sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
# piper keeps the best checkpoints by val_mos (UTMOS via torch.hub). Where UTMOS can't load (Lightning AI's Python 3.14,
# 2026-10-09), val_mos is never logged and current Lightning raises instead of skipping that callback: drop it
# (the val_mel and last.ckpt checkpoints stay)
main_py = 'src/piper/train/__main__.py'
src = open(main_py).read()
open(main_py, 'w').write(re.sub(r'\n\s*ModelCheckpoint\(\s*monitor="val_mos".*?\),(?=\n)', '', src, flags=re.S))
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
if not RESUME and not os.path.exists(f'{W}/base.ckpt'):
    sh(f'wget -q -O {W}/base.ckpt "{CKPT_URL}"')
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name en_miles',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice en-us',
    f'--data.cache_dir {W}/cache',
    f'--data.config_path {W}/out/en_miles-medium.onnx.json',
    '--data.batch_size 16',
    '--data.num_workers 2',
    '--data.dataset_type phoneme_ids',
    '--data.num_symbols 256',
    f'--data.phonemes_path {DATA}/phonemes.json',
    f'--ckpt_path {RESUME}' if RESUME else f'--model.warmstart_ckpt {W}/base.ckpt',
    f"--trainer.max_epochs {'2' if SMOKE and not RESUME else '3000'}",
    f'--trainer.max_time {MAX_TIME}',
    '--trainer.accelerator gpu --trainer.devices 1',
    f'--trainer.check_val_every_n_epoch {1 if SMOKE else 50}',
    f'--trainer.default_root_dir {W}/train',
]))
last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))[-1]
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/en_miles-medium.onnx')

# Samples: never fatal - after a 7 h run a failing sample step must not leave the cache behind (2026-10-07: it did,
# and the output could no longer be listed). The samples can always be rendered on our server instead.
try:
    sh('pip install -q piper-tts')
    sys.path.insert(0, DATA)
    import wave  # noqa: E402

    import numpy as np  # noqa: E402

    from piper import PiperVoice  # noqa: E402
    from respell import en_phonemes  # noqa: E402

    voice = PiperVoice.load(f'{W}/out/en_miles-medium.onnx', config_path=f'{W}/out/en_miles-medium.onnx.json')
    for i, text in enumerate(SAMPLES):
        audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(en_phonemes(voice, text)))
        with wave.open(f'{W}/out/sample{i}.wav', 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            w.writeframes((audio.clip(-1, 1) * 32767).astype('int16').tobytes())
except Exception as e:  # noqa: BLE001
    print('samples skipped:', e, flush=True)
sh(f'cp {last} {W}/out/last.ckpt')
cleanup()
print('done')
