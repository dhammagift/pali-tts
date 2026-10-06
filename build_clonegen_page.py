"""30 random clips of the synthetic dataset (Kaggle dg-clone-gen: Chatterbox clone of the owner's voice, Whisper-
filtered) on one page, to hear the stress errors before a Piper voice is trained on them.
Usage (on f3): python3 build_clonegen_page.py /root/clone/gen-out [name] -> out/<name>/, site/<name>.html (name: clonegen)
"""
import json
import random
import re
import subprocess
import sys
import time
import zipfile

SRC = sys.argv[1]
NAME = sys.argv[2] if len(sys.argv) > 2 else 'clonegen'
OUT = f'out/{NAME}'
kept = json.load(open(f'{SRC}/kept.json', encoding='utf-8'))
pick = random.Random(7).sample(kept, 30)
subprocess.run(['mkdir', '-p', OUT], check=True)
ver = int(time.time())
with zipfile.ZipFile(f'{SRC}/clips.zip') as z:
    for k in pick:
        z.extract(f"{k['name']}.wav", '/tmp/clonegen')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f"/tmp/clonegen/{k['name']}.wav", '-q:a', '5',
                        f"{OUT}/{k['name']}.mp3"], check=True)
phrases = [{'id': k['name'], 'text': k['text'], 'note': '✓ правильно, ✗ ошибка; нажми на слово с неправильным ударением',
            'ipa': '', 'script': '', 'section': f'Датасет клона: 30 случайных из {len(kept)}', 'multi': True,
            'words': re.findall(r'[^\s—–]+', k['text']),
            'variants': [{'id': 'c', 'letter': 'клон', 'label': f"Whisper: {k['cer'] * 100:.0f}% ошибок по буквам",
                          'src': f"audio/{NAME}/{k['name']}.mp3?v={ver}"}]} for k in pick]
page = open('page_template.html', encoding='utf-8').read()
page = (page.replace('__TITLE__', 'Датасет твоего голоса: проверка ударений')
        .replace('__INTRO__', f'Клон начитал {len(kept)} фраз ({sum(k["sec"] for k in kept) / 3600:.1f} ч, тексты с расставленными ударениями), Whisper отсеял брак.' + ' Здесь 30 случайных. Проверь ударения и чтение: если ошибок мало — учим на них Piper, если много — расставлю ударения в тексте и начитаю заново. Нажми на слово с неправильным ударением.')
        .replace('__DATA__', json.dumps({'round': NAME, 'phrases': phrases}, ensure_ascii=False)))
open(f'site/{NAME}.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases))
