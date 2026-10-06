"""Kaggle GPU job: a synthetic Russian dataset in the owner's voice. Chatterbox Multilingual (MIT) clones the voice
from an 18 s reference and reads DG translation sentences; Whisper large-v3-turbo transcribes every clip and only
clips whose transcript matches the text (CER <= 8%) are kept (the "4 words" Piper recipe: Whisper as the filter).
Stops at 1.3 h of kept audio or a 6 h budget. Sentences come with stress marks (stress_ru.py): Chatterbox's own
stresser is not installable on Kaggle, without marks every clip had stress errors. Output: /kaggle/working/clips.zip (22.05 kHz mono wavs) + kept.json
"""
import glob
import json
import os
import re
import subprocess
import time
import zipfile

START = time.time()
BUDGET = 6 * 3600
TARGET = 1.3 * 3600  # seconds of kept audio: enough for a fine-tune, and the GPU quota is 30 h a week
subprocess.run('pip install -q chatterbox-tts', shell=True, check=True)
subprocess.run('pip uninstall -y -q torchvision', shell=True)  # chatterbox pins torch; Kaggle's torchvision breaks transformers
import librosa  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: E402
from transformers import WhisperForConditionalGeneration, WhisperProcessor  # noqa: E402

W = '/kaggle/working'
REF = glob.glob('/kaggle/input/**/ru.wav', recursive=True)[0]
SENTS = open(glob.glob('/kaggle/input/**/sentences.txt', recursive=True)[0], encoding='utf-8').read().split('\n')
os.makedirs(f'{W}/wavs', exist_ok=True)
tts = ChatterboxMultilingualTTS.from_pretrained(device='cuda')
ASR = 'openai/whisper-large-v3-turbo'  # called directly: the pipeline wants torchcodec, which has no ffmpeg libs here
proc = WhisperProcessor.from_pretrained(ASR)
whisper = WhisperForConditionalGeneration.from_pretrained(ASR, torch_dtype=torch.float16).to('cuda')


def transcribe(audio22):
    feats = proc(librosa.resample(audio22, orig_sr=22050, target_sr=16000), sampling_rate=16000,
                 return_tensors='pt').input_features.to('cuda', torch.float16)
    with torch.no_grad():
        ids = whisper.generate(feats, language='ru', task='transcribe')
    return proc.batch_decode(ids, skip_special_tokens=True)[0]


def norm(s):
    return re.sub(r'[^а-я ]', '', s.lower().replace('ё', 'е').replace('-', ' ')).split()


def cer(a, b):
    a, b = ' '.join(norm(a)), ' '.join(norm(b))
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
    return d[len(b)] / max(len(a), 1)


kept, total = [], 0.0
for n, text in enumerate(s for s in SENTS if s.strip()):
    if time.time() - START > BUDGET or total > TARGET:
        break
    wav = tts.generate(text, language_id='ru', audio_prompt_path=REF)[0].cpu().numpy()
    audio = librosa.resample(wav, orig_sr=tts.sr, target_sr=22050)
    audio, _ = librosa.effects.trim(audio, top_db=35)
    heard = transcribe(audio)
    c = cer(text, heard)
    if c <= 0.08 and 1.0 < len(audio) / 22050 < 15:
        name = f'c{n:05d}'
        sf.write(f'{W}/wavs/{name}.wav', audio, 22050, subtype='PCM_16')
        kept.append({'name': name, 'text': text, 'cer': round(c, 3), 'sec': round(len(audio) / 22050, 2)})
        total += len(audio) / 22050
    if n % 25 == 0:
        print(n, 'kept', len(kept), f'{total / 60:.1f} min', f'{(time.time() - START) / 60:.0f} min elapsed', flush=True)
        json.dump(kept, open(f'{W}/kept.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(kept, open(f'{W}/kept.json', 'w', encoding='utf-8'), ensure_ascii=False)
with zipfile.ZipFile(f'{W}/clips.zip', 'w') as z:  # one file: thousands of outputs hit Kaggle's listing rate limit
    for k in kept:
        z.write(f'{W}/wavs/{k["name"]}.wav', f'{k["name"]}.wav')
subprocess.run(f'rm -rf {W}/wavs', shell=True)
print('done', len(kept), 'clips', f'{total / 3600:.2f} h')
