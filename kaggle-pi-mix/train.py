"""Kaggle GPU job: a two-speaker Pali voice from rohan (the only Hindi voice with published training weights) on
pali-mix-voice-data (make_pi_mix_dataset.py): speaker 'pratham' = pratham's own readings (its timbre and quality),
speaker 'owner' = the owner's 2 h (his pronunciation; ṁ as ŋ, ṭṭh as ʈʈʰ, symbols only his half has). The aim: speaker
pratham with the owner's symbols. Samples: speaker pratham with our rules, and with plain to_ipa (the owner's symbols).
SMOKE=1 runs a few minutes to validate the environment.
"""
import glob
import os
import re
import subprocess
import sys

SMOKE = os.environ.get('SMOKE', '0') == '1' or bool(glob.glob('/kaggle/input/**/SMOKE', recursive=True))
MAX_TIME = '00:00:12:00' if SMOKE else os.environ.get('MAX_TIME', '00:10:15:00')  # Kaggle sessions stop at 12 h; leave time for export
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
    subprocess.run(f'rm -rf {W}/cache {W}/rohan.ckpt {W}/piper1-gpl', shell=True)


sh('nvidia-smi --query-gpu=name,memory.total --format=csv')
if not os.path.exists(f'{W}/piper1-gpl'):
    sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
# legacy TorchScript exporter: torch >= 2.9 defaults to dynamo, which cannot trace VITS (run v4 died there)
sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
main_py = 'src/piper/train/__main__.py'
src = open(main_py).read()
open(main_py, 'w').write(re.sub(r'\n\s*ModelCheckpoint\(\s*monitor="val_mos".*?\),(?=\n)', '', src, flags=re.S))
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
if not os.path.exists(f'{W}/rohan.ckpt'):
    sh(f'wget -q -O {W}/rohan.ckpt "{CKPT_URL}"')
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name pali_mix',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice hi',
    f'--data.cache_dir {W}/cache',
    f'--data.config_path {W}/out/pali_mix-medium.onnx.json',
    '--data.batch_size 24',
    '--data.num_workers 2',
    '--data.dataset_type phoneme_ids',
    '--data.num_symbols 256',
    f'--data.phonemes_path {DATA}/phonemes.json',
    f'--model.warmstart_ckpt {W}/rohan.ckpt',
    '--model.num_speakers 2',
    f"--trainer.max_epochs {'2' if SMOKE else '3000'}",
    f'--trainer.max_time {MAX_TIME}',
    '--trainer.accelerator gpu --trainer.devices 1',
    f'--trainer.check_val_every_n_epoch {1 if SMOKE else 20}',
    f'--trainer.default_root_dir {W}/train',
]))
last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))[-1]
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/pali_mix-medium.onnx')

# Samples: never fatal (they can be rendered on our server too). Speaker 0/1 per the config's speaker_id_map.
try:
    sh('pip install -q piper-tts')
    sys.path.insert(0, DATA)
    import json, wave  # noqa: E401,E402
    from piper import PiperVoice, SynthesisConfig  # noqa: E402
    from pali_ipa import to_ipa, tune  # noqa: E402
    voice = PiperVoice.load(f'{W}/out/pali_mix-medium.onnx', config_path=f'{W}/out/pali_mix-medium.onnx.json')
    spk = json.load(open(f'{W}/out/pali_mix-medium.onnx.json'))['speaker_id_map']
    for i, text in enumerate(SAMPLES):
        for tag, sid, ipa in (('pr_rules', spk['pratham'], tune(to_ipa(text, full_a=True))),
                              ('pr_owner', spk['pratham'], to_ipa(text, full_a=True)),
                              ('owner', spk['owner'], to_ipa(text, full_a=True))):
            audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), SynthesisConfig(speaker_id=sid))
            with wave.open(f'{W}/out/sample{i}.{tag}.wav', 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                w.writeframes((audio.clip(-1, 1) * 32767).astype('int16').tobytes())
except Exception as e:  # noqa: BLE001
    print('samples skipped:', e, flush=True)
sh(f'cp {last} {W}/out/last.ckpt')
cleanup()
print('done')
