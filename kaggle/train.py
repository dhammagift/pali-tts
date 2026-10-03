"""Kaggle GPU job: fine-tune Piper (VITS, medium) on the owner's Pali voice, export ONNX, render samples.

Warm-starts from the hi_IN rohan checkpoint (only Hindi voice with published training weights).
SMOKE=1 runs a few minutes to validate the environment.
"""
import glob
import os
import subprocess
import sys

SMOKE = os.environ.get('SMOKE', '1') == '1'
MAX_TIME = '00:00:20:00' if SMOKE else '00:10:15:00'  # Kaggle sessions stop at 12 h; leave time for export
W = '/kaggle/working'
DATA = os.path.dirname(glob.glob('/kaggle/input/**/metadata.csv', recursive=True)[0])
CKPT_URL = ('https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/hi/hi_IN/rohan/medium/'
            'epoch%3D3190-step%3D309852.ckpt')
SAMPLES = [
    'Evaṁ me sutaṁ — ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.',
    'Cakkhukaraṇī ñāṇakaraṇī upasamāya abhiññāya sambodhāya nibbānāya saṁvattati.',
    'Idha bhikkhu vivicceva kāmehi vivicca akusalehi dhammehi savitakkaṁ savicāraṁ vivekajaṁ pītisukhaṁ paṭhamaṁ jhānaṁ upasampajja viharati.',
    'Jātipaccayā jarāmaraṇaṁ sokaparidevadukkhadomanassupāyāsā sambhavanti.',
    'Manopubbaṅgamā dhammā, manoseṭṭhā manomayā; manasā ce paduṭṭhena, bhāsati vā karoti vā.',
]


def sh(cmd):
    print('+', cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


sh('nvidia-smi --query-gpu=name,memory.total --format=csv')
if not os.path.exists(f'{W}/piper1-gpl'):
    sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
sh("pip install -q cython scikit-build 'cmake<4' ninja -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
if not os.path.exists(f'{W}/rohan.ckpt'):
    sh(f'wget -q -O {W}/rohan.ckpt "{CKPT_URL}"')
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name pali_dg',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice hi',
    f'--data.cache_dir {W}/cache',
    f'--data.config_path {W}/out/pali_dg-medium.onnx.json',
    '--data.batch_size 24',
    '--data.num_workers 2',
    '--data.dataset_type phoneme_ids',
    '--data.num_symbols 256',
    f'--data.phonemes_path {DATA}/phonemes.json',
    f'--model.warmstart_ckpt {W}/rohan.ckpt',
    '--trainer.max_epochs 3000',
    f'--trainer.max_time {MAX_TIME}',
    '--trainer.accelerator gpu --trainer.devices 1',
    f'--trainer.check_val_every_n_epoch {1 if SMOKE else 20}',
    f'--trainer.default_root_dir {W}/train',
]))
last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))[-1]
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/pali_dg-medium.onnx')

# Samples with the exported voice and our Pali IPA
sh('pip install -q piper-tts')
sys.path.insert(0, DATA)
import wave  # noqa: E402

from piper import PiperVoice  # noqa: E402
from pali_ipa import to_ipa  # noqa: E402

voice = PiperVoice.load(f'{W}/out/pali_dg-medium.onnx', config_path=f'{W}/out/pali_dg-medium.onnx.json')
for i, text in enumerate(SAMPLES):
    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(to_ipa(text, full_a=True))))
    with wave.open(f'{W}/out/sample{i}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes((audio.clip(-1, 1) * 32767).astype('int16').tobytes())
sh(f'cp {last} {W}/out/last.ckpt && rm -rf {W}/cache {W}/rohan.ckpt {W}/piper1-gpl')
print('done')
