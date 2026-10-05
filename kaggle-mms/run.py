"""Kaggle CPU job: facebook/mms-tts-rus (VITS) -> ONNX for the DG voice service (onnxruntime, no torch on
the server). Writes out/mms-tts-rus.onnx, out/mms-tts-rus.json (vocab and tokenizer settings) and a test wav.
"""
import json
import os
import subprocess

subprocess.run('pip install -q transformers onnx onnxruntime soundfile', shell=True, check=True)
import numpy as np
import onnxruntime as ort
import soundfile as sf
import torch
from transformers import AutoTokenizer, VitsModel

OUT = '/kaggle/working/out'
os.makedirs(OUT, exist_ok=True)
tok = AutoTokenizer.from_pretrained('facebook/mms-tts-rus')
model = VitsModel.from_pretrained('facebook/mms-tts-rus').eval()
cfg = model.config
print('rate', cfg.sampling_rate, 'add_blank', tok.add_blank, 'normalize', tok.normalize, 'uroman', getattr(tok, 'is_uroman', None), flush=True)


class Wrap(torch.nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, input_ids, noise_scale, noise_scale_duration, speaking_rate):
        self.m.noise_scale = noise_scale
        self.m.noise_scale_duration = noise_scale_duration
        self.m.speaking_rate = speaking_rate
        return self.m(input_ids=input_ids).waveform


# the model reads noise_scale / speaking_rate from attributes: export with them as plain floats baked in, and
# keep only input_ids dynamic (speed is changed afterwards by the service)
model.noise_scale, model.noise_scale_duration, model.speaking_rate = 0.667, 0.8, 1.0
ids = tok('проверка связи', return_tensors='pt').input_ids
torch.onnx.export(model, (ids,), f'{OUT}/mms-tts-rus.onnx', input_names=['input_ids'], output_names=['waveform'],
                  dynamic_axes={'input_ids': {1: 'n'}, 'waveform': {1: 't'}}, opset_version=17, dynamo=False)
vocab = tok.get_vocab()
json.dump({'vocab': vocab, 'add_blank': tok.add_blank, 'normalize': tok.normalize, 'pad_id': tok.pad_token_id,
           'sample_rate': cfg.sampling_rate}, open(f'{OUT}/mms-tts-rus.json', 'w', encoding='utf-8'), ensure_ascii=False)
s = ort.InferenceSession(f'{OUT}/mms-tts-rus.onnx', providers=['CPUExecutionProvider'])
text = 'И что такое, монахи, боль? Это называется, монахи, боль. День, кровь, жизнь.'
ids2 = tok(text, return_tensors='np').input_ids
wav = s.run(None, {'input_ids': ids2.astype(np.int64)})[0][0]
sf.write(f'{OUT}/test.wav', wav, cfg.sampling_rate)
with torch.no_grad():
    ref = model(input_ids=torch.tensor(ids2)).waveform[0].numpy()
print('onnx samples', len(wav), 'torch samples', len(ref), 'size MB', os.path.getsize(f'{OUT}/mms-tts-rus.onnx') / 1e6, flush=True)
print('tokens', tok.convert_ids_to_tokens(ids2[0])[:40])
