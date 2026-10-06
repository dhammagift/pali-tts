"""30 random clips of the synthetic dataset (Kaggle dg-clone-gen: Chatterbox clone of the owner's voice, Whisper-
filtered) on one page, to hear the stress errors before a Piper voice is trained on them.
Usage (on f3): python3 build_clonegen_page.py /root/clone/gen-out -> out/clonegen/, site/clonegen.html
"""
import json
import random
import re
import subprocess
import sys
import time
import zipfile

SRC = sys.argv[1]
OUT = 'out/clonegen'
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
            'ipa': '', 'script': '', 'section': 'Датасет клона: 30 случайных из 882', 'multi': True,
            'words': re.findall(r'[^\s—–]+', k['text']),
            'variants': [{'id': 'c', 'letter': 'клон', 'label': f"Whisper: {k['cer'] * 100:.0f}% ошибок по буквам",
                          'src': f"audio/clonegen/{k['name']}.mp3?v={ver}"}]} for k in pick]
page = open('page_template.html', encoding='utf-8').read()
page = (page.replace('__TITLE__', 'Датасет твоего голоса: проверка ударений')
        .replace('__INTRO__', 'Клон начитал 882 фразы (1,3 ч), Whisper отсеял брак. Здесь 30 случайных. Проверь ударения и чтение: если ошибок мало — учим на них Piper, если много — расставлю ударения в тексте и начитаю заново. Нажми на слово с неправильным ударением.')
        .replace('__DATA__', json.dumps({'round': 'clonegen', 'phrases': phrases}, ensure_ascii=False)))
open('site/clonegen.html', 'w', encoding='utf-8').write(page)
print('ok', len(phrases))
