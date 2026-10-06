"""Kaggle GPU job: fine-tune Piper (VITS, medium) from ru_RU-ruslan on the owner's Russian voice as cloned by
Chatterbox (dataset ru-dg-voice-data: 790 clips, 1.04 h, make_ru_voice_dataset.py), export ONNX, render samples.
Phoneme ids are what tts_server gives a Russian voice (espeak via ruslan + the soft-sign fix in respell.py).
SMOKE=1 runs a few minutes to validate the environment.
"""
import glob
import os
import subprocess
import sys

SMOKE = os.environ.get('SMOKE', '0') == '1'
MAX_TIME = '00:00:20:00' if SMOKE else '00:07:00:00'  # 7 h: enough for a same-language fine-tune, saves GPU quota
W = '/kaggle/working'
DATA = os.path.dirname(glob.glob('/kaggle/input/**/metadata.csv', recursive=True)[0])
CKPT_URL = ('https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/ru/ru_RU/ruslan/medium/'
            'epoch%3D2436-step%3D1724372.ckpt')
SAMPLES = [
    'Одно время Благословенный в Варанаси располагается, в Исипатане, в Оленьем Парке.',
    'И что такое, монахи, боль? Та которая, монахи, телесная боль, телесный дискомфорт, это называется, монахи, боль.',
    'День, кровь, жизнь, только учитель.',
    'Это, монахи, боль благородно-истина.',
    'Татхагата, ниббана, дхамма, сангха.',
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
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
if not os.path.exists(f'{W}/base.ckpt'):
    sh(f'wget -q -O {W}/base.ckpt "{CKPT_URL}"')
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name ru_dg',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice ru',
    f'--data.cache_dir {W}/cache',
    f'--data.config_path {W}/out/ru_dg-medium.onnx.json',
    '--data.batch_size 24',
    '--data.num_workers 2',
    '--data.dataset_type phoneme_ids',
    '--data.num_symbols 256',
    f'--data.phonemes_path {DATA}/phonemes.json',
    f'--model.warmstart_ckpt {W}/base.ckpt',
    '--trainer.max_epochs 3000',
    f'--trainer.max_time {MAX_TIME}',
    '--trainer.accelerator gpu --trainer.devices 1',
    f'--trainer.check_val_every_n_epoch {1 if SMOKE else 20}',
    f'--trainer.default_root_dir {W}/train',
]))
last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))[-1]
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/ru_dg-medium.onnx')

# Samples with the exported voice and our Pali IPA
sh('pip install -q piper-tts')
sys.path.insert(0, DATA)
import wave  # noqa: E402

import numpy as np  # noqa: E402

from piper import PiperVoice  # noqa: E402
from respell import ru_phonemes  # noqa: E402

voice = PiperVoice.load(f'{W}/out/ru_dg-medium.onnx', config_path=f'{W}/out/ru_dg-medium.onnx.json')
for i, text in enumerate(SAMPLES):
    audio = np.concatenate([voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph)) for ph in ru_phonemes(voice, text)])
    with wave.open(f'{W}/out/sample{i}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes((audio.clip(-1, 1) * 32767).astype('int16').tobytes())
sh(f'cp {last} {W}/out/last.ckpt')
cleanup()
print('done')
