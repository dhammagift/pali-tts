"""ru-accent: stress marks for Russian text, for the voice service (respell.ru_accent; owner 2026-11-17: MN 129 full of
wrong stress - дела, руки, одурманивающим - espeak has no context, and word-by-word fixes do not scale).
ruaccent (tiny mode: ~0.6 GB, ~0.16 s a line; same stresses as the full 2.2 GB one on MN 129 bar monosyllables).
POST / with the text (utf-8) -> the text with '+' before each stressed vowel. Own venv (.venv-acc: ruaccent, transformers<5),
own unit (deploy/ru-accent.service), localhost only, so the voices' venv and memory stay as they are.
"""
import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ruaccent import RUAccent

args = argparse.ArgumentParser()
args.add_argument('--port', type=int, default=3016)
args = args.parse_args()
acc = RUAccent()
acc.load(omograph_model_size='turbo3.1', use_dictionary=True, tiny_mode=True)
lock = threading.Lock()  # one model, one line at a time


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        text = self.rfile.read(min(int(self.headers.get('content-length') or 0), 64 * 1024)).decode('utf-8', 'replace')
        try:
            with lock:
                body, code = acc.process_all(text).encode('utf-8'), 200
        except Exception as e:  # the caller reads the line unmarked
            body, code = f'error: {type(e).__name__}'.encode(), 500
        self.send_response(code)
        self.send_header('content-type', 'text/plain; charset=utf-8')
        self.send_header('content-length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *a):
        pass


ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
