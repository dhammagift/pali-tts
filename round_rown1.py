"""Round rown1 (owner 2026-11-02: «100+ эпох попробуем... и с проф клоном рядом тоже»): the new local Russian voice
(Piper from ruslan on ~1300 ElevenLabs PVC lines, 149 epochs, kaggle-ru-owner) blind against the PVC itself, Puriso and
the current beta (dgru), on 6 lines of the owner's translation that were not in training. Labels never say whose voice
it is (owner 2026-11-03). All brought to one loudness. Needs a tts_server with the voice 'rown' on :3099.
Usage (on f3): .venv/bin/python round_rown1.py -> out/rown1/; then build_page.py with ROUND = 'rown1'
"""
import base64
import json
import os
import subprocess
import urllib.request

OUT, CMP = 'out/rown1', os.path.expanduser('~/pvc-dataset/cmp')
API = 'http://127.0.0.1:3099/synthesize'
VOICES = [('a', 'новый локальный голос', 'rown'), ('b', 'облачный клон (ElevenLabs)', None),
          ('c', 'Puriso', 'puriso'), ('d', 'текущая бета', 'dgru')]


def tts(text, voice):
    req = urllib.request.Request(API, json.dumps({'text': text, 'rate': 1.0, 'voice': voice}).encode(),
                                 {'Content-Type': 'application/json'})
    return base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))['audioContent'])


def level(mp3, path):
    """One loudness for all (-18 LUFS), so the louder clip does not win."""
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', '-', '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '44100',
                    '-q:a', '4', path], input=mp3, check=True)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for seg, text in json.load(open(f'{CMP}/lines.json')):
        pid = seg.replace('.', '-').replace(':', '_')
        vs = []
        for vid, label, voice in VOICES:
            f = f'{pid}.{vid}.mp3'
            level(tts(text, voice) if voice else open(f'{CMP}/pvc_{seg.replace(":", "_")}.mp3', 'rb').read(), f'{OUT}/{f}')
            vs.append({'id': vid, 'label': label, 'file': f, 'sent': ''})
        phrases.append({'id': pid, 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'{seg}. ★ лучше всех; ✓ хорошо; ✗ плохо (что не так)'})
    json.dump({'round': 'rown1', 'title': 'Русский голос — сравнение вслепую',
               'intro': 'Четыре голоса на 6 строках перевода, которых не было в обучении. Вслепую, одна громкость, 1x. '
                        'Отметьте лучший в каждой строке; «показать, кто есть кто» — после оценки.',
               'sections': [{'id': 'r', 'title': 'русский', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
