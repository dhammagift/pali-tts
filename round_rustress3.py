"""Round rustress3 (owner 2026-11-17, his Russian voice Cūḷa DG = dgru): «достопочтенный он читает с московским
акцентом» - espeak gives every unstressed o before the stress as ʌ (да-ста-па-чтенный); standard speech has ʌ only in the
syllable right before the stress and ə further back (дə-стə-па-чтенный). And «неправильное ударение в Анатхапиндики»:
the names list has -пинди́ки (penult); the Pali rule (light penult -> the heavy syllable before) gives -пи́ндики. Blind.
Usage: round_rustress3.py build"""
import base64
import json
import os
import re
import subprocess
import sys
import wave

from piper import PiperVoice, SynthesisConfig

from respell import ru_phonemes

OUT = 'out/rustress3'
MODEL = 'models/ru_owner_h3-medium'
GAIN = 1.75  # tts_server.GAIN['dgru']
V = 'aʌəɐeɛiɪyɨoɔuʊæ'


def schwa(ph):
    """Unstressed ʌ two or more syllables before the stress -> ə (the first pretonic syllable keeps ʌ)."""
    out = []
    for w in ''.join(ph).split(' '):
        k = w.find('ˈ')
        if k > 0:
            head, nv = list(w[:k]), 0
            for i in range(len(head) - 1, -1, -1):  # walk back from the stress, counting vowels
                if head[i] in V:
                    nv += 1
                    if nv >= 2 and head[i] == 'ʌ':
                        head[i] = 'ə'
            w = ''.join(head) + w[k:]
        out.append(w)
    return ' '.join(out)


PHRASES = [
    ('p00', 'Достопочтенный Сарипутта сказал так.', {'now': ('как сейчас', None), 'schwa': ('дə-стə-па-чтенный', schwa)}),
    ('p01', 'Тогда домохозяин Анатхапиндика пришёл к Благословенному.', None),
    ('p02', 'В роще Джеты, в монастыре Анатхапиндики.', None),
]

if __name__ == '__main__' and sys.argv[1:] == ['build']:
    os.makedirs(OUT, exist_ok=True)
    voice = PiperVoice.load(MODEL + '.onnx')
    cfg = SynthesisConfig(length_scale=1.0 / 0.8, noise_scale=0.6, noise_w_scale=0.7)  # the site's default 0.8x for translations

    def render(name, phonemes):
        a = sum(([voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(p)), cfg)] for p in phonemes), [])
        import numpy as np
        pcm = np.concatenate(a) * GAIN
        wav = f'{OUT}/{name}.wav'
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(voice.config.sample_rate)
            w.writeframes((pcm.clip(-1, 1) * 32767).astype('int16').tobytes())
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-q:a', '5', wav[:-4] + '.mp3'], check=True)
        os.remove(wav)
        return f'{name}.mp3'

    phrases = []
    for pid, text, var in PHRASES:
        vs = []
        if var:
            base = [''.join(p) for p in ru_phonemes(voice, text)]
            for vid, (label, f) in var.items():
                ph = [f(p) if f else p for p in base]
                vs.append({'id': vid, 'label': label, 'file': render(f'{pid}.{vid}', ph), 'sent': ' | '.join(ph)})
        else:  # stress: the names list's -пинди́ки against -пи́ндики
            for vid, label, form in (('di', '-пинди́-', 'Анатхапинди́к'), ('pi', '-пи́нди-', 'Анатхапи́ндик')):
                t = re.sub(r'Анатхапиндик', form, text)
                ph = [''.join(p) for p in ru_phonemes(voice, t)]
                if vid == 'pi':  # the names list would put its own stress back: move it by hand
                    ph = [re.sub(r'pʲindʲˈik', 'pʲˈindʲik', p) for p in ph]
                vs.append({'id': vid, 'label': label, 'file': render(f'{pid}.{vid}', ph), 'sent': ' | '.join(ph)})
        phrases.append({'id': pid, 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': 'Ваш голос (Cūḷa DG), русский. ★ лучший; ✓ правильно; ✗ неправильно'})
    json.dump({'round': 'rustress3', 'title': 'Ваш русский голос: достопочтенный, Анатхапиндика',
               'intro': '«Достопочтенный»: как сейчас (да-ста-па-чтенный) и с безударным «ə» дальше от ударения. '
                        '«Анатхапиндика»: ударение на -ди- (как сейчас) или на -пи-. Вслепую.',
               'sections': [{'id': 'p', 'title': 'Русский', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for p in phrases:
        for v in p['variants']:
            print(p['id'], v['id'], v['sent'])
