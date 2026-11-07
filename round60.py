"""Round 60 (owner 2026-11-07, Trello «Баги», MN 44): r70 fixed what the phoneme recogniser heard (ayye «ахи», pañhaṁ
lost its h), but the owner: «вопрос» (pañhaṁ) and «Айя» still sound strange. Three spellings each, all passing the
recogniser (no h in ayye; n and h in pañhaṁ), in their sentences, the way tts_server reads pratham. 0.7x.
Usage (on f3): .venv/bin/python round60.py -> out/r60/; then build_page.py with ROUND = 'r60'
"""
import json
import os
import shutil
import subprocess

from piper import PiperVoice, SynthesisConfig

from round56 import ipa

OUT = 'out/r60'
VOICE = PiperVoice.load('models/hi_IN-pratham-medium.onnx')
CFG = SynthesisConfig(length_scale=1.15 / 0.7, noise_scale=0.6, noise_w_scale=0.7)  # as tts_server at rate 0.7
AYYE = ipa('Katamo nu kho, ayye, sakkāyo vutto bhagavatā”ti?')
PANHA = ipa('Dhammadinnaṁ bhikkhuniṁ uttariṁ pañhaṁ apucchi.')
SECTIONS = [
    ('y', 'ayye', 'Katamo nu kho, ayye, sakkāyo vutto bhagavatā”ti?', AYYE, 'ˈaːɪjeː',
     [('a', 'как сейчас (r70): аай-е', 'ˈaːɪjeː'), ('b', 'долгое е в конце', 'ˈaːɪjeːeː'), ('c', 'двойное й', 'ˈaːɪjːeː')]),
    ('p', 'pañhaṁ', 'Dhammadinnaṁ bhikkhuniṁ uttariṁ pañhaṁ apucchi.', PANHA, 'pˈʌɲjhhʌn',
     [('a', 'как сейчас (r70): паньххан', 'pˈʌɲjhhʌn'), ('b', 'как в хинди: панхан', 'pˈʌnhʌn'), ('c', 'паньхам, с м', 'pˈʌɲjhhʌm')]),
]

if __name__ == '__main__':
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    sections = []
    for sid, title, text, base, now, variants in SECTIONS:
        assert now in base, base
        vs = []
        for vid, label, spelling in variants:
            f = f'{sid}.{vid}.mp3'
            pcm = VOICE.phoneme_ids_to_audio(VOICE.phonemes_to_ids(list(base.replace(now, spelling))), CFG)
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(VOICE.config.sample_rate), '-ac', '1',
                            '-i', '-', '-q:a', '7', f'{OUT}/{f}'], input=pcm.astype('float32').tobytes(), check=True)
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': ''})
        sections.append({'id': sid, 'title': title, 'multi_best': False,
                         'phrases': [{'id': sid, 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                                      'note': '✓ правильно / лучший; ✗ неправильно (что слышно)'}]})
    json.dump({'round': 'r60', 'title': 'Pali TTS — раунд 60: ayye, pañhaṁ',
               'intro': 'МН 44: «Айя» и «вопрос» звучали странно. По три варианта, все прошли распознаватель; 0.7x.',
               'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
