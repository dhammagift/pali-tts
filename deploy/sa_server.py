"""Test only (owner 2026-10-23: the Sanskrit voices on test.dhamma.gift, «по фразам трудно сказать»): AI4Bharat
vits_rasa_13 (CC BY 4.0, gated: HF_TOKEN), Sanskrit male SAN_M, book style, reading Pali written in Devanagari.
POST {"text": "<Devanagari>", "rate": 0.7} -> raw float32 PCM, sample rate in X-Sample-Rate. localhost only; the test
instance of tts_server calls it for its voice 'sanskrit' (DG_SA_URL). torch would not fit tts_server's own venv, hence
a sidecar: uv run --python 3.11 --with torch --with transformers==4.46.3 --with sentencepiece python sa_server.py
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import AutoModel, AutoTokenizer

torch.set_num_threads(1)
MODEL = 'ai4bharat/vits_rasa_13'
SAN_M, BOOK = 17, 3
model = AutoModel.from_pretrained(MODEL, trust_remote_code=True, token=os.environ['HF_TOKEN']).eval()
tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True, token=os.environ['HF_TOKEN'])
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers['content-length'])))
        with lock, torch.no_grad():
            model.speaking_rate = float(req.get('rate', 1.0))
            ids = tok(text=req['text'], return_tensors='pt')['input_ids']
            pcm = model(ids, speaker_id=SAN_M, emotion_id=BOOK).waveform.squeeze().numpy().astype('float32').tobytes()
        self.send_response(200)
        self.send_header('X-Sample-Rate', str(model.config.sampling_rate))
        self.send_header('content-length', str(len(pcm)))
        self.end_headers()
        self.wfile.write(pcm)

    def log_message(self, fmt, *a):
        pass


ThreadingHTTPServer(('127.0.0.1', 3013), Handler).serve_forever()
