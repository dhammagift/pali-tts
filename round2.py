"""Round 2: pronunciation fixes (Piper + Google) on the phrases Google won, and voice casting.

Usage: .venv/bin/python round2.py  -> out/r2/*.mp3, out/r2/index.json
"""
import base64
import json
import os
import re
import subprocess
import urllib.request

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, to_script

OUT = 'out/r2'
CFG = SynthesisConfig(length_scale=1.15, noise_scale=0.6, noise_w_scale=0.7)
KEY = json.load(open('/var/www/dg-node-test/configs/local/tts-config.json'))['key']
cases = {l.split('\t')[0]: l.rstrip('\n').split('\t')[1:] for l in list(open('cases.tsv', encoding='utf-8'))[1:]}

PRON_PHRASES = ['c9', 'c14', 'c1', 'c4', 'c5', 'c10', 'c11']
PRON = [  # (id, label, kind, params)
    ('google', 'Сейчас в DG · Google pa-IN Achird ♂', 'legacy', {}),
    ('g_knda', 'Google kn-IN Achird ♂ · пали письмом каннада', 'google', {'script': 'knda', 'voice': 'kn-IN-Chirp3-HD-Achird'}),
    ('g_telu', 'Google te-IN Achird ♂ · пали письмом телугу', 'google', {'script': 'telu', 'voice': 'te-IN-Chirp3-HD-Achird'}),
    ('p_ng', 'Piper pratham ♂ · конечное ṁ = ŋ (как в 1 раунде)', 'piper', {'model': 'hi_IN-pratham-medium', 'final_m': False}),
    ('p_m', 'Piper pratham ♂ · конечное ṁ = m', 'piper', {'model': 'hi_IN-pratham-medium', 'final_m': True}),
]

CAST_PHRASE = 'c9'
CAST = [('cast_' + m.split('-')[0][:2] + '_' + m.split('-')[1] + ('' if s is None else f'_{s}'), m, s) for m, s in
        [('hi_IN-pratham-medium', None), ('hi_IN-priyamvada-medium', None),
         ('ml_IN-arjun-medium', None), ('ml_IN-meera-medium', None),
         ('te_IN-venkatesh-medium', None), ('te_IN-maya-medium', None), ('te_IN-padmavathi-medium', None),
         ('ne_NP-chitwan-medium', None), ('ur_PK-fasih-medium', None), ('ur_PK-aegis_female-medium', None)]
        + [('mr_IN-google-medium', i) for i in range(9)] + [('ne_NP-google-medium', i) for i in range(18)]]
CAST_GOOGLE = ['Achird', 'Charon', 'Fenrir', 'Iapetus', 'Kore', 'Aoede', 'Leda', 'Sulafat']

voices = {}


def piper(path, text, model, final_m=True, speaker=None):
    if model not in voices:
        voices[model] = PiperVoice.load(f'models/{model}.onnx')
    v = voices[model]
    ipa = to_ipa(text, full_a=True, final_m=final_m, lang=v.config.espeak_voice[:2])
    cfg = SynthesisConfig(speaker_id=speaker, length_scale=CFG.length_scale,
                          noise_scale=CFG.noise_scale, noise_w_scale=CFG.noise_w_scale)
    audio = v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), cfg)
    pcm = (np.clip(audio, -1, 1) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(v.config.sample_rate), '-ac', '1',
                    '-i', '-', '-b:a', '64k', path], input=pcm, check=True)
    return ipa


def google(path, text, voice, script=None, ssml=False):
    if ssml:
        # one <phoneme> per word: a single long tag makes Google drop most of the audio
        ssml = re.sub(r"[^\s,.;:?!—–“”‘’]+", lambda m: f'<phoneme alphabet="ipa" ph="{to_ipa(m.group(), full_a=True, final_m=True)}">{m.group()}</phoneme>', text)
        inp = {'ssml': f'<speak>{ssml}</speak>'}
        shown = to_ipa(text, full_a=True, final_m=True)
    else:
        shown = to_script(text, script)
        inp = {'text': shown}
    body = json.dumps({'input': inp, 'voice': {'languageCode': voice[:5], 'name': voice},
                       'audioConfig': {'audioEncoding': 'MP3'}}).encode()
    req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize?key=' + KEY, body,
                                 {'content-type': 'application/json', 'Referer': 'https://dhamma.gift/'})
    open(path, 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=30))['audioContent']))
    return shown


def render(path, fn):
    if not os.path.exists(path):
        return fn()
    return None


os.makedirs(OUT, exist_ok=True)
sections = []
items = []
for cid in PRON_PHRASES:
    text, note = cases[cid]
    vs = []
    for vid, label, kind, p in PRON:
        f = f'{OUT}/{cid}.{vid}.mp3'
        if kind == 'legacy':
            subprocess.run(['cp', f'out/{cid}.google.mp3', f], check=True)
        elif kind == 'google':
            render(f, lambda: google(f, text, p['voice'], p.get('script'), p.get('ssml', False)))
        else:
            render(f, lambda: piper(f, text, p['model'], p['final_m']))
        vs.append({'id': vid, 'label': label, 'file': os.path.basename(f)})
    items.append({'id': cid, 'text': text, 'note': note, 'ipa': to_ipa(text, full_a=True, final_m=True),
                  'script': to_script(text, 'knda'), 'variants': vs})
    print('pron', cid)
sections.append({'id': 'pron', 'title': 'Произношение', 'multi_best': False, 'phrases': items})

text, note = cases[CAST_PHRASE]
vs = []
for vid, model, spk in CAST:
    f = f'{OUT}/cast.{vid}.mp3'
    render(f, lambda: piper(f, text, model, True, spk))
    vs.append({'id': vid, 'label': f'Piper {model.replace("-medium", "")}' + ('' if spk is None else f' · диктор {spk}'),
               'file': os.path.basename(f)})
for name in CAST_GOOGLE:
    vid = 'g_' + name.lower()
    f = f'{OUT}/cast.{vid}.mp3'
    render(f, lambda: google(f, text, 'kn-IN-Chirp3-HD-' + name, 'knda'))
    vs.append({'id': vid, 'label': f'Google kn-IN {name} (облако) · письмом каннада', 'file': os.path.basename(f)})
sections.append({'id': 'cast', 'title': 'Подбор голосов', 'multi_best': True,
                 'phrases': [{'id': 'cast', 'text': text, 'note': 'одна фраза разными голосами: ★ — нравится тембр (можно несколько)',
                              'ipa': '', 'script': '', 'variants': vs}]})
json.dump({'round': 'r2', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('cast', len(vs))
