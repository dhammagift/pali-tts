"""Kaggle GPU job: pratham's timbre with a Sanskrit voice's pronunciation (owner 2026-10-23: «обучай санскритский, он
звучит неприятно из-за тембра»).
1. Indic Parler-TTS (Aryan; round sa1: 4 of 5 ok) reads ~2400 Pali sentences in Devanagari (dataset pi-sa-texts,
   make_pi_sa_dataset.py; the gated weights in dataset indic-parler-tts-weights), batched, for at most GEN_MIN minutes;
2. kNN-VC (bshall/knn-vc, MIT) turns each take into pratham's timbre (matching set: pratham's own readings, ref/);
3. Piper fine-tuned from pratham itself (dataset pratham-ckpt) on those takes, inputs = plain to_ipa ids (no tune():
   those rules fix pratham's Hindi habits, the teacher has none) -> a 'pi-own'-style voice.
SMOKE=1: 16 sentences and a few minutes of training, to prove the environment.
"""
import glob
import os
import re
import subprocess
import sys
import time

INPUT = os.environ.get('INPUT', '/kaggle/input')
SMOKE = os.environ.get('SMOKE', '0') == '1' or bool(glob.glob(f'{INPUT}/**/SMOKE', recursive=True))
MAX_TIME = '00:00:08:00' if SMOKE else os.environ.get('MAX_TIME', '00:04:00:00')  # owner: 4 h a voice
GEN_MIN = 3 if SMOKE else 80  # minutes of Parler at most: the rest of the session is training
W = os.environ.get('WORK', '/kaggle/working')
T = os.path.dirname(glob.glob(f'{INPUT}/**/texts.csv', recursive=True)[0])
PARLER = os.path.dirname(glob.glob(f'{INPUT}/**/model.safetensors', recursive=True)[0])
DATA = f'{W}/data'
DESC = ('Aryan speaks at a moderate pace in a calm, clear voice, reading a text aloud. '
        'The recording is of very high quality with no background noise.')
SAMPLES = [
    'Evaṁ me sutaṁ — ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.',
    'Itthirūpaṁ, bhikkhave, purisassa cittaṁ pariyādāya tiṭṭhatī”ti.',
    'Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.',
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
    subprocess.run(f'rm -rf {W}/cache {W}/piper1-gpl {DATA} {W}/src', shell=True)


def make_data():
    import soundfile as sf
    import torch
    import torchaudio
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    rows = [r.split('|') for r in open(f'{T}/texts.csv', encoding='utf-8').read().split('\n') if r]
    rows = rows[:16] if SMOKE else rows
    model = ParlerTTSForConditionalGeneration.from_pretrained(PARLER, torch_dtype=torch.float16).to('cuda')
    tok = AutoTokenizer.from_pretrained(PARLER)
    dtok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    sr = model.config.sampling_rate
    os.makedirs(f'{W}/src', exist_ok=True)
    t0, done, B = time.time(), [], 16
    for k in range(0, len(rows), B):
        if time.time() - t0 > GEN_MIN * 60:
            break
        batch = rows[k:k + B]
        d = dtok([DESC] * len(batch), return_tensors='pt', padding=True).to('cuda')
        p = tok([b[1] for b in batch], return_tensors='pt', padding=True).to('cuda')
        with torch.no_grad():
            g = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask, prompt_input_ids=p.input_ids,
                               prompt_attention_mask=p.attention_mask, do_sample=True, return_dict_in_generate=True,
                               max_new_tokens=1300)
        for i, (name, text, ids) in enumerate(batch):
            a = g.sequences[i, :g.audios_length[i]].float().cpu().numpy()
            secs = len(a) / sr
            if not 0.035 * len(text) < secs < 0.25 * len(text) + 1:  # cut short or run on: not a reading of the line
                continue
            sf.write(f'{W}/src/{name}', a, sr)
            done.append((name, text, ids))
        print('parler', len(done), 'of', k + len(batch), round((time.time() - t0) / 60, 1), 'min', flush=True)
    del model
    torch.cuda.empty_cache()

    knn = torch.hub.load('bshall/knn-vc', 'knn_vc', prematched=True, pretrained=True, device='cuda')

    def wav16(f):  # tensors, not paths: knn-vc's own torchaudio.load needs torchcodec in new torchaudio
        w, s = sf.read(f, dtype='float32')
        return torchaudio.functional.resample(torch.from_numpy(w), s, 16000)[None]
    # no VAD: pratham's readings have no long silences, and VAD emptied some clips (en-miles-vc smoke run)
    matching = knn.get_matching_set([wav16(f) for f in sorted(glob.glob(f'{T}/ref/*.wav'))], vad_trigger_level=0)
    os.makedirs(f'{DATA}/wavs', exist_ok=True)
    meta = []
    for name, text, ids in done:
        out = knn.match(knn.get_features(wav16(f'{W}/src/{name}')), matching, topk=4).cpu()
        out = torch.cat([torch.zeros(1600), out, torch.zeros(2400)])  # 0.1 s before, 0.15 s after, as Piper voices end
        sf.write(f'{DATA}/wavs/{name}', torchaudio.functional.resample(out, 16000, 22050).numpy(), 22050, subtype='PCM_16')
        meta.append(f'{name}|{text}|{ids}')
    open(f'{DATA}/metadata.csv', 'w', encoding='utf-8').write('\n'.join(meta) + '\n')
    sh(f'cp {T}/phonemes.json {DATA}/ && rm -rf {W}/src')
    print('data', len(meta), flush=True)


sh('nvidia-smi --query-gpu=name,memory.total --format=csv')
sh('pip install -q git+https://github.com/huggingface/parler-tts.git soundfile')
make_data()
if not os.path.exists(f'{W}/piper1-gpl'):
    sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
main_py = 'src/piper/train/__main__.py'
src = open(main_py).read()
open(main_py, 'w').write(re.sub(r'\n\s*ModelCheckpoint\(\s*monitor="val_mos".*?\),(?=\n)', '', src, flags=re.S))
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx onnxscript -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
BASE = glob.glob(f'{INPUT}/**/pratham.ckpt', recursive=True)[0]
os.makedirs(f'{W}/out', exist_ok=True)
sh(' '.join([
    'python -m piper.train fit',
    '--data.voice_name pali_sa',
    f'--data.csv_path {DATA}/metadata.csv',
    f'--data.audio_dir {DATA}/wavs',
    '--model.sample_rate 22050',
    '--data.espeak_voice hi',
    f'--data.cache_dir {W}/cache',
    f'--data.config_path {W}/out/pali_sa-medium.onnx.json',
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
sh(f'python -m piper.train.export_onnx --checkpoint {last} --output-file {W}/out/pali_sa-medium.onnx')
try:  # samples: never fatal; they can be rendered on our server too
    sh('pip install -q piper-tts')
    sys.path.insert(0, T)
    import wave  # noqa: E402

    from piper import PiperVoice  # noqa: E402
    from pali_ipa import to_ipa  # noqa: E402

    voice = PiperVoice.load(f'{W}/out/pali_sa-medium.onnx', config_path=f'{W}/out/pali_sa-medium.onnx.json')
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
