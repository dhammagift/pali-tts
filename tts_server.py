"""DG voice service: Piper voices, answers like Google TTS ({"audioContent": base64 mp3}).

Pali (voice "pratham", the default) goes through our IAST->IPA rules; translation voices (alan, norman,
kathleen: English; irina, ruslan: Russian) use Piper's own espeak phonemizer.
POST /synthesize  body: {"text": "...", "voice": "pratham", "rate": 1.0}   (localhost only; dg-fastify
                  proxies /api/tts/pali)
GET  /health, /voices
mp3 files are cached on disk by sha1(voice + rules version + rate + text): a re-read sutta costs no CPU.
Voices load on first use and at most MAX_LOADED stay in memory (~130 MB each).
Usage: .venv/bin/python tts_server.py [--port 3011]
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
from respell import respell

RULES_VERSION = 'r14'  # bump when pali_ipa rules change, so cached mp3 are not reused
MAX_CHARS = 2000
MAX_LOADED = 3
VOICES = {  # id -> (model file, language); 'pi' voices are fed our Pali IPA
    'pratham': ('hi_IN-pratham-medium', 'pi'),
    'alan': ('en_GB-alan-medium', 'en'),
    'norman': ('en_US-norman-medium', 'en'),
    'kathleen': ('en_US-kathleen-low', 'en'),
    'irina': ('ru_RU-irina-medium', 'ru'),
    'ruslan': ('ru_RU-ruslan-medium', 'ru'),
}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'tts')
SENTENCE = re.compile(r'(?<=[.?!;:])\s+')

args = argparse.ArgumentParser()
args.add_argument('--port', type=int, default=3011)
args = args.parse_args()
MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
busy = threading.Semaphore(2)  # 2 vCPU: more parallel syntheses only slow each other down
loaded, load_lock = {}, threading.Lock()  # insertion order = least recently used first
os.makedirs(CACHE, exist_ok=True)


def get_voice(vid):
    with load_lock:
        if vid in loaded:
            loaded[vid] = loaded.pop(vid)  # mark as recently used
        else:
            while len(loaded) >= MAX_LOADED:  # evict the least recently used, but keep the Pali voice
                loaded.pop(next(v for v in loaded if v != 'pratham'))
            loaded[vid] = PiperVoice.load(os.path.join(MODELS, VOICES[vid][0] + '.onnx'))
        return loaded[vid]


def synth(text, vid, rate):
    """Sentence by sentence (VITS degrades on very long inputs), short pauses between."""
    voice, lang = get_voice(vid), VOICES[vid][1]
    sr = voice.config.sample_rate
    # Pali: our tuned pace (length 1.15 at rate 1); translations: the voice's own pace
    cfg = SynthesisConfig(length_scale=(1.15 if lang == 'pi' else 1.0) / rate, noise_scale=0.6, noise_w_scale=0.7)
    parts = []
    for sent in SENTENCE.split(text.strip()):
        if lang == 'pi':
            ipa = tune(to_ipa(sent, full_a=True))
            phonemes = [list(ipa)] if ipa.strip(' ,.?!') else []
        else:
            phonemes = [p for p in voice.phonemize(respell(sent, lang)) if p]  # Pali words in a translation
        for ph in phonemes:
            parts.append(voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph), cfg))
        if phonemes:
            parts.append(np.zeros(int(sr * 0.35), dtype=np.float32))
    pcm = np.concatenate(parts) if parts else np.zeros(sr // 4, dtype=np.float32)
    return subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-',
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
        if self.path == '/health':
            return self.reply(200, {'ok': True, 'loaded': list(loaded), 'rules': RULES_VERSION})
        if self.path == '/voices':
            return self.reply(200, {vid: lang for vid, (_, lang) in VOICES.items()})
        self.reply(404, {'error': {'message': 'not found'}})

    def do_POST(self):
        if self.path != '/synthesize':
            return self.reply(404, {'error': {'message': 'not found'}})
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get('content-length', 0)), 64 * 1024)))
            text = str(req.get('text', ''))[:MAX_CHARS]
            rate = min(max(float(req.get('rate', 1.0)), 0.25), 3.0)
            vid = str(req.get('voice') or 'pratham')
        except (ValueError, TypeError):
            return self.reply(400, {'error': {'message': 'bad request'}})
        if vid not in VOICES:
            return self.reply(400, {'error': {'message': 'unknown voice'}})
        if not text.strip():
            return self.reply(400, {'error': {'message': 'empty text'}})
        key = hashlib.sha1(f'{VOICES[vid][0]}|{RULES_VERSION}|{rate:.2f}|{text}'.encode()).hexdigest()
        path = os.path.join(CACHE, key + '.mp3')
        if not os.path.exists(path):
            with busy:
                mp3 = synth(text, vid, rate)
            tmp = path + '.tmp'
            open(tmp, 'wb').write(mp3)
            os.replace(tmp, path)
        self.reply(200, {'audioContent': base64.b64encode(open(path, 'rb').read()).decode()})

    def log_message(self, fmt, *a):  # keep journald quiet: one line per synthesis is enough
        pass


ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
