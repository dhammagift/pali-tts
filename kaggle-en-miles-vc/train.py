"""Kaggle GPU job: Miles's voice v3 (owner 2026-10-23). His 300 takes (~20 min) are too little for Piper, so:
1. ryan (the base Miles liked best, round miles5) reads ~2600 Sujato sentences (dataset en-miles-vc-texts, ids from
   make_en_miles_vc_texts.py), each with a tail word after it, cut where ryan's own durations say the tail starts
   (ryan cuts a line's last sound: round miles5);
2. kNN-VC (bshall/knn-vc, MIT) turns every clip into Miles's timbre, his 300 takes the matching set;
3. Piper fine-tuned from ryan on those clips plus his own 300 takes (each three times: the real voice weighs more).
Exports ONNX + samples; last.ckpt kept. SMOKE=1: 20 texts and a few minutes of training, to prove the environment.
"""
import glob
import os
import re
import subprocess
import sys

INPUT = os.environ.get('INPUT', '/kaggle/input')
SMOKE = os.environ.get('SMOKE', '0') == '1' or bool(glob.glob(f'{INPUT}/**/SMOKE', recursive=True))
MAX_TIME = '00:00:08:00' if SMOKE else os.environ.get('MAX_TIME', '00:04:00:00')  # owner: 4 h a voice
W = os.environ.get('WORK', '/kaggle/working')
REAL = os.path.dirname(glob.glob(f'{INPUT}/**/metadata.csv', recursive=True)[0])  # en-miles-voice-data
TEXTS = glob.glob(f'{INPUT}/**/texts.csv', recursive=True)[0]  # en-miles-vc-texts
RYAN = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx'
CKPT_URL = 'https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/en/en_US/ryan/medium/epoch%3D4641-step%3D3104302.ckpt'
TAIL = ' ænd'  # round miles5: "and" after the sentence, cut away
DATA = f'{W}/data'
SAMPLES = [
    'So I have heard. At one time the Buddha was staying near Sāvatthī in Jeta’s Grove, Anāthapiṇḍika’s monastery.',
    'There the Buddha addressed the mendicants, “Mendicants!”',
    'And what, mendicants, is suffering? Rebirth is suffering, old age is suffering, death is suffering.',
    'by name-matter conditioned is the six-fold area;',
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
    subprocess.run(f'rm -rf {W}/cache {W}/base.ckpt {W}/piper1-gpl {DATA} {W}/src {W}/ryan*', shell=True)


def make_data():
    """ryan reads the texts (tail cut), kNN-VC to Miles; plus the real takes x3. -> DATA/wavs + metadata.csv"""
    import numpy as np
    import onnx
    import onnxruntime as ort
    import soundfile as sf
    import torch
    import torchaudio

    sh(f'wget -q -O {W}/ryan.onnx "{RYAN}" && wget -q -O {W}/ryan.onnx.json "{RYAN}.json"')
    m = onnx.load(f'{W}/ryan.onnx')
    m.graph.output.append(onnx.helper.make_tensor_value_info('/Ceil_output_0', onnx.TensorProto.FLOAT, None))
    onnx.save(m, f'{W}/ryan.align.onnx')
    import json
    idmap = json.load(open(f'{W}/ryan.onnx.json'))['phoneme_id_map']
    tail_ids = [i for c in TAIL for i in idmap[c] + idmap['_']]
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(f'{W}/ryan.align.onnx', so, providers=['CPUExecutionProvider'])
    rows = [r.split('|') for r in open(TEXTS, encoding='utf-8').read().split('\n') if r]
    rows = rows[:20] if SMOKE else rows
    os.makedirs(f'{W}/src', exist_ok=True)
    for name, text, ids in rows:
        ids = list(map(int, ids.split()))
        n = (len(ids) - 3) // 2  # ^ _ (p _)* $: phonemes in the sentence
        full = ids[:-1] + tail_ids + ids[-1:]
        audio, dur = sess.run(None, {'input': np.array([full], dtype=np.int64), 'input_lengths': np.array([len(full)], dtype=np.int64),
                                     'scales': np.array([0.6, 1.0, 0.7], dtype=np.float32)})
        audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * 256
        end = int(np.cumsum(dur)[2 * n + 1])  # the tail's leading space starts here
        a = audio[:end].astype(np.float32)
        a[-660:] *= np.linspace(1, 0, 660, dtype=np.float32)
        sf.write(f'{W}/src/{name}', np.concatenate([np.zeros(2205, np.float32), a, np.zeros(3300, np.float32)]), 22050)
    print('ryan read', len(rows), flush=True)

    knn = torch.hub.load('bshall/knn-vc', 'knn_vc', trust_repo=True, prematched=True, pretrained=True, device='cuda' if torch.cuda.is_available() else 'cpu')
    def wav16(f):  # tensors, not paths: knn-vc's own torchaudio.load needs torchcodec in new torchaudio
        wav, sr = sf.read(f, dtype='float32')
        return torchaudio.functional.resample(torch.from_numpy(wav), sr, 16000)[None]
    # no VAD: the takes are trimmed already, and its trim left some empty (conv1d on 0 samples)
    matching = knn.get_matching_set([wav16(f) for f in sorted(glob.glob(f'{REAL}/wavs/*.wav'))], vad_trigger_level=0)
    os.makedirs(f'{DATA}/wavs', exist_ok=True)
    meta = []
    for name, text, ids in rows:
        out = knn.match(knn.get_features(wav16(f'{W}/src/{name}')), matching, topk=4).cpu()
        sf.write(f'{DATA}/wavs/{name}', torchaudio.functional.resample(out, 16000, 22050).numpy(), 22050, subtype='PCM_16')
        meta.append(f'{name}|{text}|{ids}')
    print('converted', len(meta), flush=True)
    for line in open(f'{REAL}/metadata.csv', encoding='utf-8').read().split('\n'):
        if not line:
            continue
        name = line.split('|')[0]
        for k in range(3):  # the real voice three times
            sh(f'cp {REAL}/wavs/{name} {DATA}/wavs/r{k}_{name}')
            meta.append(f'r{k}_{line}')
    open(f'{DATA}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(meta) + '\n')
    sh(f'cp {REAL}/phonemes.json {DATA}/')
    sh(f'rm -rf {W}/src')


sh('nvidia-smi --query-gpu=name,memory.total --format=csv')
if not os.path.exists(f'{W}/piper1-gpl'):
    sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
main_py = 'src/piper/train/__main__.py'
src = open(main_py).read()
open(main_py, 'w').write(re.sub(r'\n\s*ModelCheckpoint\(\s*monitor="val_mos".*?\),(?=\n)', '', src, flags=re.S))
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript onnxruntime soundfile -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
try:
    make_data()
except Exception:  # keep the reason, and no thousands of files in the output
    import traceback
    open(f'{W}/error.txt', 'w').write(traceback.format_exc())
    cleanup()
    raise
sh(f'wget -q -O {W}/base.ckpt "{CKPT_URL}"')
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name en_miles3',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice en-us',
    f'--data.cache_dir {W}/cache',
    f'--data.config_path {W}/out/en_miles3-medium.onnx.json',
    '--data.batch_size 16',
    '--data.num_workers 2',
    '--data.dataset_type phoneme_ids',
    '--data.num_symbols 256',
    f'--data.phonemes_path {DATA}/phonemes.json',
    f'--model.warmstart_ckpt {W}/base.ckpt',
    f"--trainer.max_epochs {'2' if SMOKE else '3000'}",
    f'--trainer.max_time {MAX_TIME}',
    '--trainer.accelerator gpu --trainer.devices 1',
    f'--trainer.check_val_every_n_epoch {1 if SMOKE else 10}',
    f'--trainer.default_root_dir {W}/train',
]))
last = sorted(glob.glob(f'{W}/train/**/last.ckpt', recursive=True))[-1]
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/en_miles3-medium.onnx')
try:  # samples: never fatal; they can be rendered on our server too
    sh('pip install -q piper-tts')
    sys.path.insert(0, REAL)
    import wave  # noqa: E402

    from piper import PiperVoice  # noqa: E402
    from respell import en_phonemes  # noqa: E402

    voice = PiperVoice.load(f'{W}/out/en_miles3-medium.onnx', config_path=f'{W}/out/en_miles3-medium.onnx.json')
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
