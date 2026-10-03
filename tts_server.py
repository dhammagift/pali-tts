"""Pali TTS service for DG: Piper voice + our IAST->IPA rules, answers like Google TTS ({"audioContent": base64 mp3}).

POST /synthesize  body: {"text": "<Pali IAST>", "rate": 1.0}   (localhost only; dg-fastify proxies /api/tts/pali)
GET  /health
mp3 files are cached on disk by sha1(voice + rules version + rate + text): a re-read sutta costs no CPU.
Usage: .venv/bin/python tts_server.py [--port 3011] [--voice hi_IN-pratham-medium]
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

RULES_VERSION = 'r12'  # bump when pali_ipa rules change, so cached mp3 are not reused
SR = 22050
MAX_CHARS = 2000
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'tts')
SENTENCE = re.compile(r'(?<=[.?!;:])\s+')

args = argparse.ArgumentParser()
args.add_argument('--port', type=int, default=3011)
args.add_argument('--voice', default='hi_IN-pratham-medium')
args = args.parse_args()
voice = PiperVoice.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', args.voice + '.onnx'))
busy = threading.Semaphore(2)  # 2 vCPU: more parallel syntheses only slow each other down
os.makedirs(CACHE, exist_ok=True)


def synth(text, rate):
    """Sentence by sentence (VITS degrades on very long inputs), short pauses between."""
    cfg = SynthesisConfig(length_scale=1.15 / rate, noise_scale=0.6, noise_w_scale=0.7)
    parts = []
    for sent in SENTENCE.split(text.strip()):
        ipa = tune(to_ipa(sent, full_a=True))
        if ipa.strip(' ,.?!'):
            parts += [voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), cfg),
                      np.zeros(int(SR * 0.35), dtype=np.float32)]
    pcm = np.concatenate(parts) if parts else np.zeros(SR // 4, dtype=np.float32)
    return subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                           '-b:a', '64k', '-f', 'mp3', '-'], input=pcm.astype(np.float32).tobytes(),
                          capture_output=True, check=True).stdout


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply(200, {'ok': True, 'voice': args.voice, 'rules': RULES_VERSION}) if self.path == '/health' \
            else self.reply(404, {'error': {'message': 'not found'}})

    def do_POST(self):
        if self.path != '/synthesize':
            return self.reply(404, {'error': {'message': 'not found'}})
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get('content-length', 0)), 64 * 1024)))
            text = str(req.get('text', ''))[:MAX_CHARS]
            rate = min(max(float(req.get('rate', 1.0)), 0.5), 2.0)
        except (ValueError, TypeError):
            return self.reply(400, {'error': {'message': 'bad request'}})
        if not text.strip():
            return self.reply(400, {'error': {'message': 'empty text'}})
        key = hashlib.sha1(f'{args.voice}|{RULES_VERSION}|{rate:.2f}|{text}'.encode()).hexdigest()
        path = os.path.join(CACHE, key + '.mp3')
        if not os.path.exists(path):
            with busy:
                mp3 = synth(text, rate)
            tmp = path + '.tmp'
            open(tmp, 'wb').write(mp3)
            os.replace(tmp, path)
        self.reply(200, {'audioContent': base64.b64encode(open(path, 'rb').read()).decode()})

    def log_message(self, fmt, *a):  # keep journald quiet: one line per synthesis is enough
        pass


ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
