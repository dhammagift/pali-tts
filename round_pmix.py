"""pratham retrained (pali_mix: pratham itself, warm-started from its rebuilt checkpoint, two speakers - pratham's own
readings + the owner's 2 h) against pratham as it is, on the owner's problem words (ṁ, ṭṭh, -uṁ, paggayha...).
Blind: (a) pratham now, our rules; (b) retrained, speaker pratham, our rules; (c) retrained, speaker pratham, plain IPA
(the owner's symbols: ṁ as ŋ, ṭṭh as ʈʈʰ). Under each line, openly labelled: the retrained model's owner speaker.
Usage (f3): .venv/bin/python round_pmix.py /root/pimix-out/full/out -> out/pmix/; then a build_page copy with ROUND = 'pmix'
"""
import json
import os
import subprocess
import sys

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

MODEL_DIR = sys.argv[1]
OUT = 'out/pmix'
TEXTS = ['Evaṁ me sutaṁ.', 'Dasāhaparamaṁ atirekacīvaraṁ dhāretabbaṁ.', 'Nissaggiyaṁ pācittiyaṁ.',
         'Tikkhattuṁ padakkhiṇaṁ katvā.', 'Icchāmahaṁ, ayye, vihāraṁ kātuṁ.', 'Tiṭṭhantu, bhikkhave, satta vassāni.',
         'Uddiṭṭhaṁ kho āyasmanto nidānaṁ.', 'Niṭṭhite navakamme ca, sammādiṭṭhi.', 'Samādāya paggayha aṭṭhāsi.',
         'Ayampi pārājiko hoti asaṁvāso.', 'Tasmā tuṇhī, evametaṁ dhārayāmīti.', 'Katamā ca, bhikkhave, jarā?']
LENGTH = 1.15 / 0.7  # the rounds' 0.7x


def mp3(audio, f):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-af', 'loudnorm=I=-18:TP=-1.5', '-q:a', '5', f'{OUT}/{f}'], input=audio.astype(np.float32).tobytes(), check=True)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    now = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
    new = PiperVoice.load(f'{MODEL_DIR}/pali_mix-medium.onnx', config_path=f'{MODEL_DIR}/pali_mix-medium.onnx.json')
    spk = new.config.speaker_id_map
    sections = []
    for i, text in enumerate(TEXTS):
        rules, plain = tune(to_ipa(text, full_a=True)), to_ipa(text, full_a=True)
        cfg = lambda sid=None: SynthesisConfig(length_scale=LENGTH, noise_scale=0.6, noise_w_scale=0.7, speaker_id=sid)
        vs = []
        for vid, label, voice, ipa, sid in (('a', 'pratham сейчас (наши правила)', now, rules, None),
                                            ('b', 'pratham переученный, наши правила', new, rules, spk['pratham']),
                                            ('c', 'pratham переученный, твои обозначения (ṁ = ŋ, ṭṭh)', new, plain, spk['pratham'])):
            for take in (1, 2):
                f = f'p{i}.{vid}{take}.mp3'
                mp3(voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), cfg(sid)), f)
                vs.append({'id': f'{vid}{take}', 'label': f'{label} · дубль {take}', 'file': f, 'sent': ipa})
        sections.append({'id': f'p{i}', 'title': f'Фраза {i + 1}: вслепую', 'multi_best': False, 'phrases': [
            {'id': f'p{i}', 'text': text, 'ipa': rules, 'script': '', 'variants': vs, 'note': '★ где правильно и голос хороший'}]})
        f = f'p{i}.own.mp3'
        mp3(new.phoneme_ids_to_audio(new.phonemes_to_ids(list(plain)), cfg(spk['owner'])), f)
        sections.append({'id': f'ref{i}', 'title': f'Фраза {i + 1}: для справки', 'multi_best': True, 'phrases': [
            {'id': f'ref{i}', 'text': text, 'ipa': plain, 'script': '', 'note': 'оценивать не нужно',
             'variants': [{'id': 'own', 'label': 'та же модель, твой голос (диктор owner)', 'file': f, 'sent': plain}]}]})
    json.dump({'round': 'pmix', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(TEXTS), 'lines')
