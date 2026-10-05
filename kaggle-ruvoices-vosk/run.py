"""Kaggle CPU job (Vosk only, the first run picked the wrong Vosk model): the same Russian lines (SN 56.11 in the owner's translation + the player's demo lines)
read by every open Russian TTS that runs without a GPU, for a listening page. Each engine is tried on its
own; a failure is written to errors.txt and the rest still run. Output: out/<engine>_<voice>_<n>.mp3, out/index.json
"""
import json
import os
import subprocess
import sys
import traceback

W = '/kaggle/working'
OUT = f'{W}/out'
os.makedirs(OUT, exist_ok=True)
LINES = [
    'Одно время Благословенный в Варанаси располагается, в Исипатане, в Оленьем Парке. Здесь Благословенный к группе пяти монахов обратился:',
    '«Две границы, монахи, отшельником не должны быть затронуты. Какие две?»',
    'Это именно этот благородный восьмеричный путь, в частности: правильный взгляд, правильное намерение, правильная речь.',
    'И что такое, монахи, боль? Та которая, монахи, телесная боль, телесный дискомфорт, это называется, монахи, боль.',
]
index = []
errors = []


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(cmd + '\n' + r.stdout[-2000:] + r.stderr[-2000:])


def to_mp3(wav, name):
    sh(f'ffmpeg -loglevel error -y -i "{wav}" -ac 1 -af loudnorm=I=-18:TP=-1.5 -ar 24000 -q:a 5 "{OUT}/{name}.mp3"')
    os.remove(wav)
    return f'{name}.mp3'


def engine(name, licence, fn):
    try:
        for voice, files in fn():
            index.append({'engine': name, 'voice': voice, 'licence': licence, 'files': files})
        print('ok', name, flush=True)
    except Exception:
        errors.append(f'== {name}\n{traceback.format_exc()[-3000:]}')
        print('FAILED', name, flush=True)


def piper_voices():
    sh('pip install -q piper-tts')
    from piper import PiperVoice
    import wave
    for v in ['ruslan', 'irina', 'denis', 'dmitri']:
        base = f'https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/{v}/medium/ru_RU-{v}-medium.onnx'
        sh(f'wget -q -O {W}/{v}.onnx "{base}" && wget -q -O {W}/{v}.onnx.json "{base}.json"')
        voice = PiperVoice.load(f'{W}/{v}.onnx')
        files = []
        for n, t in enumerate(LINES):
            wav = f'{W}/p_{v}_{n}.wav'
            with wave.open(wav, 'wb') as w:
                voice.synthesize_wav(t, w)
            files.append(to_mp3(wav, f'piper_{v}_{n}'))
        yield v, files


def silero():
    import torch, soundfile as sf
    model, _ = torch.hub.load('snakers4/silero-models', 'silero_tts', language='ru', speaker='v4_ru', trust_repo=True)
    for v in ['aidar', 'baya', 'kseniya', 'xenia', 'eugene']:
        files = []
        for n, t in enumerate(LINES):
            audio = model.apply_tts(text=t, speaker=v, sample_rate=48000)
            wav = f'{W}/s_{v}_{n}.wav'
            sf.write(wav, audio.numpy(), 48000)
            files.append(to_mp3(wav, f'silero_{v}_{n}'))
        yield v, files


def vosk():
    sh('pip install -q vosk-tts')
    from vosk_tts import Model, Synth
    model = Model(model_name='vosk-model-tts-ru-0.9-multi')  # lang='ru' picked the speech-recognition model
    synth = Synth(model)
    for sid in range(0, 5):
        files = []
        for n, t in enumerate(LINES):
            wav = f'{W}/v_{sid}_{n}.wav'
            synth.synth(t, wav, speaker_id=sid)
            files.append(to_mp3(wav, f'vosk_{sid}_{n}'))
        yield f'speaker {sid}', files


def mms():
    sh('pip install -q transformers')
    import torch, soundfile as sf
    from transformers import VitsModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained('facebook/mms-tts-rus')
    model = VitsModel.from_pretrained('facebook/mms-tts-rus')
    files = []
    for n, t in enumerate(LINES):
        with torch.no_grad():
            audio = model(**tok(t, return_tensors='pt')).waveform[0].numpy()
        wav = f'{W}/m_{n}.wav'
        sf.write(wav, audio, model.config.sampling_rate)
        files.append(to_mp3(wav, f'mms_rus_{n}'))
    yield 'mms-tts-rus', files


engine('Vosk TTS', 'Apache 2.0 (alphacep vosk-tts)', vosk)
json.dump({'lines': LINES, 'voices': index}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if errors:
    open(f'{W}/errors.txt', 'w').write('\n'.join(errors))
print('done', len(index), 'voices')
