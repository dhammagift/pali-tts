"""Kaggle GPU job: pratham with Google's Sanskrit pronunciation (owner 2026-11-16, round gsa1: Google's reading in
pratham's timbre «намного лучше»; DG's own site only). Data: kernel gsa-data (Google sa-IN readings of 2400 canon
sentences, kNN-VC to pratham's timbre, recogniser scores). Piper fine-tuned from pratham itself (dataset pratham-ckpt),
inputs = plain to_ipa ids (no tune(): those fix pratham's Hindi habits, the teacher has none).
SMOKE file in an input or SMOKE=1: a few minutes of training, to prove the environment.
"""
import glob
import os
import re
import subprocess
import sys

INPUT = os.environ.get('INPUT', '/kaggle/input')
SMOKE = False  # smoke run 2026-11-16: 2352 clips, 88 steps an epoch at 0.38 it/s (~4 min), export ok
MAX_TIME = '00:00:08:00' if SMOKE else os.environ.get('MAX_TIME', '00:08:00:00')
W = os.environ.get('WORK', '/kaggle/working')
T = os.path.dirname(glob.glob(f'{INPUT}/**/texts.csv', recursive=True)[0])
# run 2 (owner 2026-11-16 «обучим»): every part (gsa-data: s00000-s02399, gsa-data-b0..b3: s02400-s14399, ~25 h)
TARS = sorted(glob.glob(f'{INPUT}/**/gsa-data*.tar', recursive=True))
SCORES = sorted(glob.glob(f'{INPUT}/**/*scores.tsv', recursive=True))
# from scores.tsv of run 1 (2389 clips: whole median 0.86, p5 0.73): 2352 kept; the worst ones are repeats Google
# misread or swallowed (mano ca pāpako, sassaṁghātaṁ)
WHOLE_MIN, TAIL_MIN = 0.6, 0.5
# ~25 h of wavs plus Piper's cache (audio and spectrogram tensors, several times the wavs) do not fit the 20 GB of
# /kaggle/working: both go to the big scratch disk
TMP = os.environ.get('TMPWORK', '/tmp/gsa')
DATA = f'{TMP}/data'
SAMPLES = [
    'Evaṁ me sutaṁ — ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.',
    'Itthirūpaṁ, bhikkhave, purisassa cittaṁ pariyādāya tiṭṭhatī”ti.',
    'Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.',
    'Tiṭṭhatu, bhikkhave, ekaṁ vassaṁ.',
    'Yāyaṁ taṇhā ponobbhavikā nandīrāgasahagatā.',
    'Paṭhamaṁ.',
    'Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.',
    'Idamavoca bhagavā.',
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
    # thousands of files make the kernel output listing hit Kaggle's API rate limit: keep only out/
    subprocess.run(f'rm -rf {TMP} {W}/piper1-gpl {W}/train', shell=True)


sh('nvidia-smi --query-gpu=name,memory.total --format=csv; df -h /tmp /kaggle/working')
print('tars', TARS, 'scores', SCORES, flush=True)
meta = []
for k, tar in enumerate(TARS):  # each tar holds data/{wavs,metadata.csv,phonemes.json}: merged into one data/
    sh(f'mkdir -p {TMP}/part{k} {DATA}/wavs && tar -xf {tar} -C {TMP}/part{k} && cp {TMP}/part{k}/data/phonemes.json {DATA}/'
       f' && find {TMP}/part{k}/data/wavs -name "*.wav" -exec mv -t {DATA}/wavs {{}} +')
    meta += [m for m in open(f'{TMP}/part{k}/data/metadata.csv', encoding='utf-8').read().split('\n') if m]
    sh(f'rm -rf {TMP}/part{k}')
# the clips the recogniser heard as the text: whole and last quarter (a cut or garbled end is left out)
good = {r.split('\t')[0] for f in SCORES for r in open(f, encoding='utf-8').read().split('\n')[1:] if r
        and float(r.split('\t')[1]) >= WHOLE_MIN and float(r.split('\t')[2]) >= TAIL_MIN}
meta = [m for m in meta if m.split('|')[0] in good]
open(f'{DATA}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(meta) + '\n')
print('clips kept', len(meta), flush=True)
sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
main_py = 'src/piper/train/__main__.py'
src = open(main_py).read()
open(main_py, 'w').write(re.sub(r'\n\s*ModelCheckpoint\(\s*monitor="val_mos".*?\),(?=\n)', '', src, flags=re.S))
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
# run 2 goes on from run 1 (44 epochs on 2352 clips); pratham.ckpt only if run1.ckpt is missing
BASE = (glob.glob(f'{INPUT}/**/run1.ckpt', recursive=True) or glob.glob(f'{INPUT}/**/pratham.ckpt', recursive=True))[0]
print('base', BASE, flush=True)
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name pali_gsa',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice hi',
    f'--data.cache_dir {TMP}/cache',
    f'--data.config_path {W}/out/pali_gsa-medium.onnx.json',
    '--data.batch_size 24',
    '--data.num_workers 2',
    '--data.dataset_type phoneme_ids',
    '--data.num_symbols 256',
    f'--data.phonemes_path {DATA}/phonemes.json',
    f'--model.warmstart_ckpt {BASE}',
    f"--trainer.max_epochs {'2' if SMOKE else '3000'}",
    f'--trainer.max_time {MAX_TIME}',
    '--trainer.accelerator gpu --trainer.devices 1',
    f'--trainer.check_val_every_n_epoch {1 if SMOKE else 10}',
    f'--trainer.default_root_dir {W}/train',
]))
last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))[-1]
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/pali_gsa-medium.onnx')
try:  # samples: never fatal; they can be rendered on our server too
    sh('pip install -q piper-tts')
    sys.path.insert(0, T)
    import wave  # noqa: E402

    from piper import PiperVoice  # noqa: E402
    from pali_ipa import to_ipa  # noqa: E402

    voice = PiperVoice.load(f'{W}/out/pali_gsa-medium.onnx', config_path=f'{W}/out/pali_gsa-medium.onnx.json')
    for i, text in enumerate(SAMPLES):
        audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(to_ipa(text, full_a=True))))
        with wave.open(f'{W}/out/sample{i}.wav', 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            w.writeframes((audio.clip(-1, 1) * 32767).astype('int16').tobytes())
except Exception as e:  # noqa: BLE001
    print('samples skipped:', e, flush=True)
sh(f'cp {last} {W}/out/last.ckpt')
cleanup()
print('done')
