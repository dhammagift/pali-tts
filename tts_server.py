"""DG voice service: Piper voices, answers like Google TTS ({"audioContent": base64 mp3}).

Pali (voice "pratham", the default) goes through our IAST->IPA rules; translation voices (alan, norman,
kathleen: English; irina, ruslan: Russian) use Piper's own espeak phonemizer.
POST /synthesize  body: {"text": "...", "voice": "pratham", "rate": 1.0}
POST /memo        body: {"segments": [...], "voice", "rate", "delay": s, "end_delay": s, "sound": "gong.mp3"}
                  -> audio/mpeg: the lines with silences of any length between them (Memo page download;
                  Google's SSML stops at 10 s pauses)
GET  /health, /voices
GET  /offline/pali-ipa.json, /offline/pali-tts.js, /offline/<voice>.onnx(.json): what DG needs to read on the device
     with no network (web/pali-tts.js + onnxruntime-web): the rules as data, the engine, the model; for the en/ru voices
     also /offline/espeak.mjs + espeak.wasm (web/espeak) and /offline/espeak-<core|en|ru>.bin (piper's espeak-ng-data)
Reachable from the internet through Apache/Cloudflare (like Google's TTS API): CORS is open and each
client IP gets RATE_LIMIT requests per minute (CF-Connecting-IP / X-Forwarded-For).
mp3 files are cached on disk by sha1(voice + rules version + rate + text): a re-read sutta costs no CPU.
The cache is capped (--cache-mb) and also shrinks when the disk runs low (--min-free-mb): least recently
played files go first, popular suttas stay.
Voices load on first use and at most MAX_LOADED stay in memory (~130 MB each).
Usage: .venv/bin/python tts_server.py [--port 3011] [--max-loaded 3] [--cache-mb 1000] [--min-free-mb 1500]
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import export, to_ipa, tune
from respell import en_phonemes, export as respell_export, respell, ru_phonemes

RULES_VERSION = 'r40'  # bump when pali_ipa rules change, so cached mp3 are not reused
MAX_CHARS = 2000
RATE_LIMIT = 60  # requests per client IP per minute
# id -> (model file, language, menu label). Sites build their voice menus from GET /voices (in this order; the first
# voice of a language is its default), so a voice is added, renamed or dropped here only, not in DG's voice.js.
# 'pi*' voices are fed our Pali IPA. Male voices first, then female (owner: the order of the suttas' own lists).
VOICES = {
    'pratham': ('hi_IN-pratham-medium', 'pi', 'pratham ♂ · Piper'),
    # the owner's own voice, fine-tuned on their readings (v1, epoch 179: round 13); trained on plain to_ipa
    'dg': ('pali_dg-medium', 'pi-own', 'o Dhamma.Gift ♂ · beta'),
    # female Pali voice (round 44: ok 20 of 22 with pratham's rules, as they are)
    'priyamvada': ('hi_IN-priyamvada-medium', 'pi', 'priyamvada ♀ · Piper'),
    'alan': ('en_GB-alan-medium', 'en', 'alan ♂ · UK'),
    'norman': ('en_US-norman-medium', 'en', 'norman ♂ · US'),
    'kathleen': ('en_US-kathleen-low', 'en', 'kathleen ♀ · US (low)'),
    # the owner's timbre: Piper fine-tuned from ruslan on 1 h read by a Chatterbox clone of his voice (2026-10-07)
    'dgru': ('ru_dg2-medium', 'ru', 'o Dhamma.Gift ♂ · beta'),
    'ruslan': ('ru_RU-ruslan-medium', 'ru', 'ruslan ♂'),
    'irina': ('ru_RU-irina-medium', 'ru', 'irina ♀'),
}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'tts')
SENTENCE = re.compile(r'(?<=[.?!;:])\s+')

args = argparse.ArgumentParser()
args.add_argument('--port', type=int, default=3011)
args.add_argument('--host', default='127.0.0.1')
args.add_argument('--max-loaded', type=int, default=3, help='voices kept in memory (~130 MB each)')
args.add_argument('--cache-mb', type=int, default=1000, help='mp3 cache size cap')
args.add_argument('--min-free-mb', type=int, default=1500, help='shrink the cache while the disk has less free')
args = args.parse_args()
MAX_LOADED = args.max_loaded
MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
# a copy without some models (the Hugging Face Space has no own voice) just serves fewer voices
VOICES = {k: v for k, v in VOICES.items() if os.path.exists(os.path.join(MODELS, v[0] + '.onnx'))}
busy = threading.Semaphore(2)  # 2 vCPU: more parallel syntheses only slow each other down
loaded, load_lock = {}, threading.Lock()  # insertion order = least recently used first
hits, hits_lock = {}, threading.Lock()  # ip -> (window start minute, count)


def prune_cache(folder, cap_bytes, min_free_bytes=0):
    """Drop least recently used mp3 (mtime is refreshed on every hit) until the cache is 90% of the cap,
    and further while the disk has less than min_free_bytes free (the servers are short on space)."""
    files = []
    for name in os.listdir(folder):
        try:
            st = os.stat(os.path.join(folder, name))
            files.append((st.st_mtime, st.st_size, name))
        except FileNotFoundError:
            pass
    total = sum(f[1] for f in files)
    shortfall = max(0, min_free_bytes - shutil.disk_usage(folder).free)
    if total <= cap_bytes and not shortfall:
        return 0
    target = min(cap_bytes * 0.9, total - shortfall * 1.1)
    removed = 0
    for _, size, name in sorted(files):
        if total <= target:
            break
        try:
            os.remove(os.path.join(folder, name))
            total -= size
            removed += 1
        except FileNotFoundError:
            pass
    return removed


writes, writes_lock = 0, threading.Lock()


def note_write():
    global writes
    with writes_lock:
        writes += 1
        due = writes % 50 == 0
    if due:  # every 50 new files; listing a few thousand names is cheap
        threading.Thread(target=prune_cache, args=(CACHE, args.cache_mb * 2 ** 20, args.min_free_mb * 2 ** 20),
                         daemon=True).start()


def rate_limited(ip):
    # ponytail: fixed one-minute window in memory, reset on restart; enough for one small server
    minute = int(time.time() // 60)
    with hits_lock:
        if len(hits) > 10000:
            hits.clear()
        start, count = hits.get(ip, (minute, 0))
        count = count + 1 if start == minute else 1
        hits[ip] = (minute, count)
        return count > RATE_LIMIT
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


aligned, HOP = {}, 256  # voice id -> onnx session that also gives per-phoneme durations (or None: no such file)


def align_session(vid):
    """models/<model>.align.onnx: the voice with its duration node (/Ceil) as a second output, made by
    round26.align_model(). Loaded on first use, kept."""
    with load_lock:
        if vid not in aligned:
            path = os.path.join(MODELS, VOICES[vid][0] + '.align.onnx')
            import onnxruntime  # piper's own dependency
            aligned[vid] = onnxruntime.InferenceSession(path, providers=['CPUExecutionProvider']) if os.path.exists(path) else None
        return aligned[vid]


def lone_word(vid, ipa, cfg):
    """A word on its own (a rule's title: Sañcaritta, Aññabhāgiya) is misread far worse than inside a sentence. Round 50:
    read inside "W, W." with the second W cut out by the model's own durations, 4 of 6 ok; with a full stop 2 of 6;
    alone 0 of 6. Without an align model, the full stop."""
    sess = align_session(vid)
    voice = get_voice(vid)
    if sess is None:
        return voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa + '.')), cfg)
    ids = voice.phonemes_to_ids(list(f'{ipa}, {ipa}.'))  # ^ _ (phoneme _)* $
    audio, dur = sess.run(None, {'input': np.array([ids], dtype=np.int64), 'input_lengths': np.array([len(ids)], dtype=np.int64),
                                 'scales': np.array([cfg.noise_scale, cfg.length_scale, cfg.noise_w_scale], dtype=np.float32)})
    audio, dur = audio.reshape(-1), dur.reshape(-1).astype(int) * HOP
    starts = np.concatenate([[0], np.cumsum(dur)])
    first = starts[2 + 2 * (len(ipa) + 2)]  # the second W's first phoneme, after ", "
    return audio[max(first - int(0.03 * voice.config.sample_rate), 0):].astype(np.float32)


def synth(text, vid, rate):
    pcm, sr = synth_pcm(text, vid, rate)
    return encode_mp3(pcm, sr)


# MP3 VBR ~40 kbit/s (LAME -q:a 7). Round 19, blind, the same audio: 64, 48 and ~40 sounded alike,
# 32 (Google's rate) was worse in 3 of 4 lines; ~40 is 37% less traffic and cache than the old 64 CBR.
MP3_QUALITY = '7'


def encode_mp3(pcm, sr):
    # Into a file, not a pipe: only then can ffmpeg go back and write the Xing header, without which
    # players show a wrong length for VBR and seek badly. Long silences cost next to nothing in VBR.
    with tempfile.NamedTemporaryFile(suffix='.mp3') as f:
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-',
                        '-q:a', MP3_QUALITY, f.name], input=pcm.astype(np.float32).tobytes(), check=True)
        return open(f.name, 'rb').read()


def synth_pcm(text, vid, rate):
    """Sentence by sentence (VITS degrades on very long inputs), short pauses between."""
    voice, lang = get_voice(vid), VOICES[vid][1]
    sr = voice.config.sample_rate
    # pratham: our tuned pace (length 1.15 at rate 1); own voice and translations: the recorded pace
    cfg = SynthesisConfig(length_scale=(1.15 if lang == 'pi' else 1.0) / rate, noise_scale=0.6, noise_w_scale=0.7)
    parts = []
    for sent in SENTENCE.split(text.strip()):
        if lang.startswith('pi'):
            ipa = to_ipa(sent, full_a=True)
            ipa = tune(ipa) if lang == 'pi' else ipa  # pratham's fixes would only confuse the own voice
            phonemes = [list(ipa)] if ipa.strip(' ,.?!') else []
        elif lang == 'en':  # Pali words in an English translation get our phonemes (dhamma, sutta)
            phonemes = [p for p in [en_phonemes(voice, sent)] if p]
        elif lang == 'ru':  # Pali words in Cyrillic, and the soft sign espeak loses (боль, день, кровь)
            phonemes = [p for p in ru_phonemes(voice, sent) if p]
        else:
            phonemes = [p for p in voice.phonemize(respell(sent, lang)) if p]  # Pali words in a translation
        word = ipa.strip(' ,.?!:;') if lang == 'pi' else ''
        if word and ' ' not in word:
            parts.append(lone_word(vid, word, cfg))
            phonemes = []  # read
            parts.append(np.zeros(int(sr * 0.35), dtype=np.float32))
        for ph in phonemes:
            parts.append(voice.phoneme_ids_to_audio(voice.phonemes_to_ids(ph), cfg))
        if phonemes:
            parts.append(np.zeros(int(sr * 0.35), dtype=np.float32))
    pcm = np.concatenate(parts) if parts else np.zeros(sr // 4, dtype=np.float32)
    if lang == 'pi-own' and np.abs(pcm).max() > 0:  # its recordings were quiet: comes out ~16 dB under pratham
        pcm = pcm * (0.9 / np.abs(pcm).max())
    return pcm, sr


SOUNDS = '/var/www/html/assets/sounds'
MEMO_LIMITS = {'segments': 200, 'chars': 20000, 'delay': 3600, 'end_delay': 3600, 'speech_minutes': 30, 'minutes': 180}   # pauses in seconds


class MemoLimit(ValueError):
    """A limit the Memo page's request ran into: `code` lets the page say it in the reader's language."""
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code, self.extra = code, extra


def human(seconds):
    m = round(seconds / 60)
    return f"{m // 60} h {m % 60} min" if m >= 60 and m % 60 else (f"{m // 60} h" if m >= 60 else f"{m} min")


def memo_mp3(segments, vid, rate, delay, end_delay, sound):
    """The Memo page's lines read one after another with `delay` seconds of silence between them, then
    an optional sound and `end_delay` of silence, as one mp3.

    Two limits, because they cost different things: SPEECH (the synthesis, CPU) at most speech_minutes,
    the WHOLE file at most minutes. Silence costs next to nothing, so it is not held in memory: it is
    fed to ffmpeg in chunks, and the pauses are known before the first word is synthesized."""
    sr = get_voice(vid).config.sample_rate
    lead, last = 1.0, (end_delay if end_delay > 0 else 0)   # lead-in silence: fade-in players swallow the first syllables
    pauses = lead + last + (delay * (len(segments) - 1) if delay > 0 else 0)
    if pauses > 60 * MEMO_LIMITS['minutes']:
        raise MemoLimit('total', f"the whole recording can be {human(60 * MEMO_LIMITS['minutes'])} at most, the pauses come to {human(pauses)}", total_sec=round(pauses))
    sound_pcm = None
    if sound:
        sound_pcm = np.frombuffer(subprocess.run(
            ['ffmpeg', '-loglevel', 'error', '-i', os.path.join(SOUNDS, sound), '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-'],
            capture_output=True, check=True).stdout, dtype=np.float32) * 0.6
    with tempfile.NamedTemporaryFile(suffix='.mp3') as f:
        # Into a file (not a pipe) so ffmpeg can go back and write the Xing header (see encode_mp3).
        proc = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-',
                                 '-q:a', MP3_QUALITY, f.name], stdin=subprocess.PIPE)
        try:
            def silence(seconds):
                left = int(sr * seconds)
                chunk = np.zeros(sr * 10, dtype=np.float32).tobytes()          # 10 s at a time
                while left > 0:
                    n = min(left, sr * 10)
                    proc.stdin.write(chunk if n == sr * 10 else np.zeros(n, dtype=np.float32).tobytes())
                    left -= n
            silence(lead)
            speech = 0.0
            for i, seg in enumerate(segments):
                pcm, _ = synth_pcm(seg, vid, rate)
                speech += len(pcm) / sr
                if speech > 60 * MEMO_LIMITS['speech_minutes']:
                    raise MemoLimit('speech', f"the speech itself can be {MEMO_LIMITS['speech_minutes']} min at most (the pauses do not count)")
                proc.stdin.write(pcm.astype(np.float32).tobytes())
                if i < len(segments) - 1 and delay > 0:
                    silence(delay)
            total = pauses + speech + (len(sound_pcm) / sr if sound_pcm is not None else 0)
            if total > 60 * MEMO_LIMITS['minutes']:
                raise MemoLimit('total', f"the whole recording would be {human(total)}, the limit is {human(60 * MEMO_LIMITS['minutes'])}", total_sec=round(total))
            if sound_pcm is not None:
                proc.stdin.write(sound_pcm.astype(np.float32).tobytes())
            silence(last)
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError('mp3 encoding failed')
        except BaseException:
            proc.kill(); proc.wait()
            raise
        return open(f.name, 'rb').read()


OWN_VOICES = {'dg', 'dgru'}  # the owner's timbre: never handed out as a file
# piper's own espeak-ng-data, in packs a device downloads once: core with the first en/ru voice, then its language
ESPEAK_DATA = os.path.join(os.path.dirname(os.path.abspath(__import__('piper').__file__)), 'espeak-ng-data')
ESPEAK_PACKS = {'core': ['phontab', 'phonindex', 'phondata', 'intonations'],
                'en': ['en_dict', 'lang/gmw/en', 'lang/gmw/en-GB-x-rp', 'lang/gmw/en-US'],
                'ru': ['ru_dict', 'lang/zle/ru']}
_packs = {}


def espeak_pack(pack, gz=False):
    """[4-byte little-endian header length][JSON header: [[path, size], ...]][the files one after another]
    (web/voice-offline.js unpacks it into espeak's file system). gz: the same gzipped, for the wire."""
    if pack not in _packs:
        files = [(f, open(os.path.join(ESPEAK_DATA, f), 'rb').read()) for f in ESPEAK_PACKS[pack]]
        head = json.dumps([[f, len(b)] for f, b in files]).encode()
        raw = len(head).to_bytes(4, 'little') + head + b''.join(b for _, b in files)
        _packs[pack] = (raw, __import__('gzip').compress(raw, 9))
    return _packs[pack][1 if gz else 0]


class Handler(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header('access-control-allow-origin', '*')
        self.send_header('access-control-allow-methods', 'GET, POST, OPTIONS')
        self.send_header('access-control-allow-headers', 'content-type')
        self.send_header('access-control-max-age', '86400')

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(body)))
        self.send_header('cache-control', 'no-store')
        self.cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # CORS preflight for JSON POSTs from other sites
        self.send_response(204)
        self.cors()
        self.end_headers()

    def client_ip(self):
        fwd = self.headers.get('cf-connecting-ip') or (self.headers.get('x-forwarded-for') or '').split(',')[0]
        return fwd.strip() or self.client_address[0]

    def do_GET(self):
        if self.path == '/health':
            return self.reply(200, {'ok': True, 'loaded': list(loaded), 'rules': RULES_VERSION})
        if self.path == '/voices':  # the menus of DG's voice.js; 'pi-own' is a Pali voice like the others
            return self.reply(200, {'voices': [{'id': vid, 'lang': lang[:2], 'label': label}
                                               for vid, (_, lang, label) in VOICES.items()]})
        if self.path.startswith('/offline/'):
            return self.offline(self.path[len('/offline/'):])
        self.reply(404, {'error': {'message': 'not found'}})

    def offline(self, name):
        """DG offline: rules + engine + models. The Pali voices fed tune()'s rules and the en/ru voices; the own voices
        (pi-own 'dg', 'dgru') stay here."""
        offered = {vid: os.path.join(MODELS, VOICES[vid][0]) for vid in VOICES
                   if VOICES[vid][1] in ('pi', 'en', 'ru') and vid not in OWN_VOICES}
        model = lambda vid: offered[vid] + '.align.onnx' if os.path.exists(offered[vid] + '.align.onnx') else offered[vid] + '.onnx'
        web = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
        if name == 'pali-ipa.json':  # 'voices': a new tag tells a device its downloaded model is stale
            return self.reply(200, {'rules': RULES_VERSION, 'data': export(), 'respell': respell_export(),
                                    'espeak': {'code': sum(os.path.getsize(os.path.join(web, 'espeak', f)) for f in ('espeak.mjs', 'espeak.wasm')),
                                               'tag': str(int(max(os.path.getmtime(os.path.join(web, 'espeak', f)) for f in ('espeak.mjs', 'espeak.wasm')))),
                                               **{pack: len(espeak_pack(pack)) for pack in ESPEAK_PACKS},
                                               'gz': {pack: len(espeak_pack(pack, gz=True)) for pack in ESPEAK_PACKS}}, 'voices': {
                vid: {'label': VOICES[vid][2], 'lang': VOICES[vid][1], 'bytes': os.path.getsize(model(vid)),
                      'tag': f'{int(os.path.getmtime(model(vid)))}'} for vid in offered}})
        m = re.fullmatch(r'([a-z]+)\.onnx(\.json)?', name)
        if name == 'pali-tts.js':
            path, ctype = os.path.join(web, 'pali-tts.js'), 'text/javascript'
        elif name in ('espeak.mjs', 'espeak.wasm'):
            path, ctype = os.path.join(web, 'espeak', name), 'text/javascript' if name.endswith('mjs') else 'application/wasm'
        elif re.fullmatch(r'espeak-([a-z]+)\.bin', name) and name[7:-4] in ESPEAK_PACKS:
            return self.send_bytes(espeak_pack(name[7:-4]), 'application/octet-stream', espeak_pack(name[7:-4], gz=True))
        elif m and m.group(1) in offered:
            path = offered[m.group(1)] + '.onnx.json' if m.group(2) else model(m.group(1))
            ctype = 'application/json' if m.group(2) else 'application/octet-stream'
        else:
            return self.reply(404, {'error': {'message': 'not found'}})
        self.send_response(200)
        self.send_header('content-type', ctype)
        self.send_header('content-length', str(os.path.getsize(path)))
        self.send_header('cache-control', 'no-cache')
        self.cors()
        self.end_headers()
        with open(path, 'rb') as f:
            shutil.copyfileobj(f, self.wfile, 1 << 20)

    def send_bytes(self, body, ctype, gz=None):
        if gz and 'gzip' in (self.headers.get('accept-encoding') or ''):  # the browser unpacks it (ru: 9 MB -> 5 MB)
            body = gz
        self.send_response(200)
        self.send_header('content-type', ctype)
        if body is gz:
            self.send_header('content-encoding', 'gzip')
            self.send_header('vary', 'accept-encoding')
        self.send_header('content-length', str(len(body)))
        self.send_header('cache-control', 'no-cache')
        self.cors()
        self.end_headers()
        self.wfile.write(body)

    def memo(self):
        try:
            req = json.loads(self.rfile.read(min(int(self.headers.get('content-length', 0)), 256 * 1024)))
            segs = [str(x).strip()[:MAX_CHARS] for x in req.get('segments', []) if str(x).strip()]
            vid = str(req.get('voice') or 'pratham')
            rate = min(max(float(req.get('rate', 1.0)), 0.25), 3.0)
            delay = max(float(req.get('delay', 2)), 0)
            end_delay = max(float(req.get('end_delay', 0)), 0)
            sound = str(req.get('sound') or '')
        except (ValueError, TypeError):
            return self.reply(400, {'error': {'message': 'bad request'}})
        if vid not in VOICES:
            return self.reply(400, {'error': {'message': 'unknown voice'}})
        if delay > MEMO_LIMITS['delay']:
            return self.reply(413, {'error': {'code': 'interval', 'message': f"the interval between lines can be {human(MEMO_LIMITS['delay'])} at most, yours is {human(delay)}"}})
        if end_delay > MEMO_LIMITS['end_delay']:
            return self.reply(413, {'error': {'code': 'end', 'message': f"the end wait can be {human(MEMO_LIMITS['end_delay'])} at most, yours is {human(end_delay)}"}})
        if sound and (sound not in ('gong.mp3', 'tick.mp3') or not os.path.exists(os.path.join(SOUNDS, sound))):
            sound = ''
        if not segs:
            return self.reply(400, {'error': {'message': 'empty text'}})
        if len(segs) > MEMO_LIMITS['segments'] or sum(map(len, segs)) > MEMO_LIMITS['chars']:
            return self.reply(413, {'error': {'code': 'size', 'message': f"at most {MEMO_LIMITS['segments']} lines and {MEMO_LIMITS['chars']} characters"}})
        try:
            with busy:
                mp3 = memo_mp3(segs, vid, rate, delay, end_delay, sound)
        except MemoLimit as e:
            return self.reply(413, {'error': {'code': e.code, 'message': str(e), **e.extra}})
        except ValueError as e:
            return self.reply(413, {'error': {'message': str(e)}})
        self.send_response(200)
        self.send_header('content-type', 'audio/mpeg')
        self.send_header('content-length', str(len(mp3)))
        self.send_header('cache-control', 'no-store')
        self.cors()
        self.end_headers()
        self.wfile.write(mp3)

    def do_POST(self):
        if self.path == '/memo':
            # one request of many lines: counts as ten against the per-IP limit
            ip = self.client_ip()
            if any(rate_limited(ip) for _ in range(10)):
                return self.reply(429, {'error': {'message': 'Too many requests, try again shortly'}})
            return self.memo()
        if self.path != '/synthesize':
            return self.reply(404, {'error': {'message': 'not found'}})
        if rate_limited(self.client_ip()):
            return self.reply(429, {'error': {'message': 'Too many requests, try again shortly'}})
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
        if os.path.exists(path):
            os.utime(path)  # recently played: keep it longer
        else:
            with busy:
                mp3 = synth(text, vid, rate)
            tmp = path + '.tmp'
            open(tmp, 'wb').write(mp3)
            os.replace(tmp, path)
            note_write()
        self.reply(200, {'audioContent': base64.b64encode(open(path, 'rb').read()).decode()})

    def log_message(self, fmt, *a):  # keep journald quiet: one line per synthesis is enough
        pass


prune_cache(CACHE, args.cache_mb * 2 ** 20, args.min_free_mb * 2 ** 20)
ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
