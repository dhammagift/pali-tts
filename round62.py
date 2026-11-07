"""Round 62 (owner 2026-11-07): the owner's Russian voice, h3 (denis base, data4, 144 epochs) against the real ElevenLabs
clips it learned from and the earlier versions (v1 = prod dgru, v2, v3 from ruslan; h2 at 89 epochs). Six lines of the
training set, and six new lines (audit/lines.json) read by ElevenLabs for this round - a fairer test; blind, all loudness-normalised the same. 1.0x.
Usage (on f3, tts_cmp on 127.0.0.1:3099): .venv/bin/python round62.py -> out/r62/; then build_page.py with ROUND = 'r62'
"""
import base64
import json
import os
import shutil
import subprocess
import urllib.request

OUT = 'out/r62'
DATA = '/root/pvc-dataset'
NAMES = ['0126_sn56.35_2.1', '0220_sn56.45_3.4', 'b0174_sn19.21_2.8', 'b0360_sn15.20_1.1', 'b0759_dn22_18.37', 'b1160_dn22_12.2']
NEW = [2, 9, 27, 39, 43, 53]  # audit lines (not in the training set), ElevenLabs takes in ~/pvc-dataset/mp3new (725 credits)
VOICES = [('rown', 'v1 (сейчас в DG)'), ('rown2', 'v2'), ('rown3', 'v3'), ('h2', 'h2 (89 эпох)'), ('h3', 'h3 (144 эпохи)')]


def norm(src, dst):  # the same loudness for every take: louder must not pass for better
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-af', 'loudnorm=I=-18:TP=-1.5', '-ar', '22050', '-ac', '1',
                    '-q:a', '4', dst], check=True)


if __name__ == '__main__':
    text = {l.split('|')[0][:-4]: l.split('|')[1] for l in open(f'{DATA}/ru-owner-data4/metadata.csv', encoding='utf-8')}
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    lines = json.load(open(f'{DATA}/audit/lines.json', encoding='utf-8'))
    items = [(f'l{k}', text[n], f'{DATA}/mp3/{n}.mp3') for k, n in enumerate(NAMES)]
    items += [(f'n{k}', lines[i][1], f'{DATA}/mp3new/a{i:03d}.mp3') for k, i in enumerate(NEW)]
    phrases = []
    for pid, line, el in items:
        norm(el, f'{OUT}/{pid}.el.mp3')
        vs = [{'id': 'el', 'label': 'ElevenLabs (исходник)', 'file': f'{pid}.el.mp3', 'sent': ''}]
        for vid, label in VOICES:
            req = urllib.request.Request('http://127.0.0.1:3099/synthesize', json.dumps({'text': line, 'rate': 1.0, 'voice': vid}).encode(),
                                         {'Content-Type': 'application/json'})
            tmp = f'{OUT}/tmp.mp3'
            open(tmp, 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))['audioContent']))
            norm(tmp, f'{OUT}/{pid}.{vid}.mp3')
            os.remove(tmp)
            vs.append({'id': vid, 'label': label, 'file': f'{pid}.{vid}.mp3', 'sent': ''})
        phrases.append({'id': pid, 'text': line, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '✓ / ✗ и комментарий: металл, роботичность, обрыв конца, похоже ли на исходник'})
    json.dump({'round': 'r62', 'title': 'Русский голос DG — раунд 62: ElevenLabs и версии v1, v2, v3, h2, h3',
               'intro': 'Шесть строк из обучающих данных и шесть новых: исходник ElevenLabs и те же строки каждой версией модели. '
                        'Вслепую, громкость выровнена; «показать, кто есть кто» — внизу. 1.0x.',
               'sections': [{'id': 'r', 'title': 'строки из обучения', 'multi_best': False, 'phrases': phrases[:len(NAMES)]},
                            {'id': 'n', 'title': 'новые строки (модель их не видела)', 'multi_best': False, 'phrases': phrases[len(NAMES):]}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok')
