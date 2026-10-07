"""Kaggle CPU job: picks the exported voice out of ru-dg-voice-train's output (that output also holds the training
cache - thousands of files that make the output listing hit Kaggle's API rate limit), renders the samples the
training job could not (its 'import piper' failed after the run), and leaves only a few files.
"""
import glob
import os
import shutil
import subprocess
import sys
import wave

W = '/kaggle/working'
src = os.path.dirname(glob.glob('/kaggle/input/**/out/ru_dg-medium.onnx', recursive=True)[0])
os.makedirs(f'{W}/out', exist_ok=True)
for f in ('ru_dg-medium.onnx', 'ru_dg-medium.onnx.json'):
    shutil.copy(f'{src}/{f}', f'{W}/out/{f}')
last = sorted(glob.glob('/kaggle/input/**/checkpoints/last.ckpt', recursive=True))
if last:
    shutil.copy(last[-1], f'{W}/out/last.ckpt')  # to continue training later
subprocess.run('pip install -q piper-tts', shell=True, check=True)
sys.path.insert(0, os.path.dirname(glob.glob('/kaggle/input/**/respell.py', recursive=True)[0]))
import numpy as np  # noqa: E402
from piper import PiperVoice  # noqa: E402

from respell import ru_phonemes  # noqa: E402

SAMPLES = ['Одно время Благословенный в Варанаси располагается, в Исипатане, в Оленьем Парке.',
           'И что такое, монахи, боль? Та которая, монахи, телесная боль, телесный дискомфорт, это называется, монахи, боль.',
           'День, кровь, жизнь, только учитель.',
           'Это, монахи, боль благородно-истина.',
           'Татхагата, ниббана, дхамма, сангха.']
voice = PiperVoice.load(f'{W}/out/ru_dg-medium.onnx', config_path=f'{W}/out/ru_dg-medium.onnx.json')
for i, text in enumerate(SAMPLES):
    audio = np.concatenate([voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph)) for ph in ru_phonemes(voice, text)])
    with wave.open(f'{W}/out/sample{i}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes((audio.clip(-1, 1) * 32767).astype('int16').tobytes())
print('done', os.listdir(f'{W}/out'))
