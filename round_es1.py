"""espeak-ng `pi` check: its own (robotic) voice on all of SN 56.11 and the words earlier rounds stumbled on.
Only correctness is judged, before Pali is offered to espeak-ng. espeak's own voice hides retroflex vs dental,
so the same espeak phonemes are also read by pratham and the own voice (as Piper would with espeak `pi`).
Usage: python3 round_es1.py -> out/es1/*.mp3, out/es1/index.json; then build_page.py with ROUND = 'es1'
"""
import json
import os
import subprocess

from piper import PiperVoice, SynthesisConfig

ESPEAK = '/root/build/espeak-ng'
OUT = 'out/es1'
SN = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms/sutta/sn/sn56/sn56.11_root-pli-ms.json'
WORDS = ['sammādiṭṭhi', 'Jarāpi dukkhā', 'ponobbhavikā', 'taṇhāya', 'ñāṇaṁ udapādi', 'paññā', 'tiparivaṭṭaṁ',
         'Ñāṇañca', 'nimmānaratī', 'Paṭhamaṁ jhānaṁ', 'passambhayaṁ kāyasaṅkhāraṁ', 'viharati', 'kiñci', 'muhuttena',
         'sokaparidevadukkhadomanassupāyāsā', 'saṅkhārapaccayā viññāṇaṁ', 'nandīrāgasahagatā', 'Dutiyaṁ',
         'appaṭivattiyaṁ', 'sammāsambodhiṁ abhisambuddho', 'saddamanussāvesuṁ', 'cakkhuṁ', 'Evaṁ me sutaṁ',
         'Namo tassa bhagavato arahato sammāsambuddhassa']


def speak(text, f):
    env = dict(os.environ, ESPEAK_DATA_PATH=f'{ESPEAK}/build')
    wav = subprocess.run([f'{ESPEAK}/build/src/espeak-ng', '-v', 'pi', '-s', '140', '--stdout', text],
                         env=env, capture_output=True, check=True).stdout
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-ac', '1', '-q:a', '6', f], input=wav, check=True)
    return subprocess.run([f'{ESPEAK}/build/src/espeak-ng', '-q', '--ipa', '-v', 'pi', text], env=env,
                          capture_output=True, text=True, check=True).stdout.replace('\n', ' ').strip()


def neural(voice, ipa, length, f):
    cfg = SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7)
    audio = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), cfg)
    if abs(audio).max() > 0:  # the own voice is quiet
        audio = audio * (0.9 / abs(audio).max())
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', '22050', '-ac', '1', '-i', '-',
                    '-q:a', '6', f], input=audio.astype('float32').tobytes(), check=True)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    voices = [('pr', 'pratham по фонемам espeak', PiperVoice.load('models/hi_IN-pratham-medium.onnx'), 1.15),
              ('dg', 'свой голос по фонемам espeak', PiperVoice.load('models/pali_dg-medium.onnx'), 1.0)]
    sutta = [(k, v.strip()) for k, v in json.load(open(SN, encoding='utf-8')).items() if v.strip()]
    sections = []
    for sid, title, items in [('w', 'Слова, на которых спотыкались раунды', list(enumerate(WORDS))),
                              ('s', 'SN 56.11 целиком', [(k.split(':')[1], t) for k, t in sutta])]:
        phrases = []
        for n, text in items:
            pid = f'{sid}{n}'.replace('.', '_')
            ipa = speak(text, f'{OUT}/{pid}.mp3')
            phrases.append({'id': pid, 'text': text, 'ipa': ipa, 'script': '', 'note': '✓ правильно / ✗ ошибка; нажми на неправильное слово',
                            'variants': [{'id': 'es', 'label': 'espeak-ng pi', 'file': f'{pid}.mp3'}]})
            for vid, label, voice, length in voices:
                neural(voice, ipa, length, f'{OUT}/{pid}.{vid}.mp3')
                phrases[-1]['variants'].append({'id': vid, 'label': label, 'file': f'{pid}.{vid}.mp3'})
        sections.append({'id': sid, 'title': title, 'multi_best': True, 'phrases': phrases})
    json.dump({'round': 'es1', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(sum(len(s['phrases']) for s in sections), 'lines')
