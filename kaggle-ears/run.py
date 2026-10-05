"""'Ears' for the Pali TTS: a phoneme recogniser (wav2vec2 trained on espeak phonemes, Common Voice) turns each
clip back into phonemes with their times, to compare with what the voice was asked to say.
Input: dataset pali-tts-ears-v1 (audio/*.mp3 + manifest.json). Output: /kaggle/working/heard.json
"""
import glob
import json
import os
import subprocess

subprocess.run('pip install -q phonemizer', shell=True)
import librosa
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

src = glob.glob('/kaggle/input/**/manifest.json', recursive=True)[0]
root = os.path.dirname(src)
man = json.load(open(src, encoding='utf-8'))
name = 'facebook/wav2vec2-lv-60-espeak-cv-ft'
proc = Wav2Vec2Processor.from_pretrained(name, do_phonemize=False)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
model = Wav2Vec2ForCTC.from_pretrained(name).to(dev).eval()
step = model.config.inputs_to_logits_ratio / 16000  # seconds per CTC frame
out = []
for n, m in enumerate(man):
    audio, _ = librosa.load(os.path.join(root, 'audio', m['file']), sr=16000)
    with torch.no_grad():
        logits = model(proc(audio, sampling_rate=16000, return_tensors='pt').input_values.to(dev)).logits
    ids = torch.argmax(logits, dim=-1)[0].cpu().numpy()
    dec = proc.tokenizer.decode(ids, output_char_offsets=True)
    m['heard'] = dec.text
    m['spans'] = [(o['char'], round(o['start_offset'] * step, 3), round(o['end_offset'] * step, 3)) for o in dec.char_offsets]
    m['seconds'] = round(len(audio) / 16000, 3)
    out.append(m)
    if n % 100 == 0:
        print(n, m['file'], '|', m['expected'][:50], '|', dec.text[:80], flush=True)
json.dump(out, open('/kaggle/working/heard.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('done', len(out))
