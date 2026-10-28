"""Round el1 (owner 2026-10-28: pratham reads unevenly, the own voice is low quality; try an ElevenLabs voice as the
next Pali voice, on the hard places): Indian voices of the ElevenLabs library (multilingual v2) reading Pali in
Devanagari (pali_ipa.to_script), against pratham as in DG (0.7x). Lines: the focus lines of site/record (ṁ endings,
ṭṭh, ṇh, the owner's misread words) + ph and long final vowels. The winner's voice would read a Piper dataset.
Usage (on f3): .venv/bin/python round_el1.py -> out/el1/; then build_page.py with ROUND = 'el1'
"""
import base64
import json
import os
import urllib.request

from pali_ipa import to_script

OUT = 'out/el1'
env = dict(l.split('=', 1) for l in open('/root/.secrets/tools.env').read().splitlines() if '=' in l and not l.startswith('#'))
H = {'xi-api-key': env['EL_TOKEN'].strip().strip('"\''), 'Content-Type': 'application/json'}
VOICES = {  # library voice id -> short name (Hindi, calm narrators)
    'qDuRKMlYmrm8trt5QyBn': 'Taksh', '4BoDaQ6aygOP6fpsUmJe': 'Raghav', 'Qxb5zQvEo3DYQK2HNnXm': 'Kunal',
    'ypnkIsDASPgHZuanrF0q': 'Rudra', 'trxRCYtDC6qFREKq6Ek2': 'Sourabh', '1qEiC6qsybMkmnNdVMbK': 'Monika'}
TEXTS = ['Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.',
         'Taṇṭhānasammajjanañca, hemantagimhavassānānaṁ.',
         'Dvattikkhattuṁ tuṇhībhāvena uddiṭṭhaṁ.',
         'parisuddhetthāyasmanto, tasmā tuṇhī, evametaṁ dhārayāmīti.',
         'rūpataṇhā, saddataṇhā, gandhataṇhā, rasataṇhā, phoṭṭhabbataṇhā, dhammataṇhā.',
         'Haneyyuṁ vā bandheyyuṁ vā pabbājeyyuṁ vā.']


def api(path, body=None):
    r = urllib.request.Request('https://api.elevenlabs.io' + path, json.dumps(body).encode() if body else None, H)
    return urllib.request.urlopen(r, timeout=120).read()


def add_to_library(vid):
    """A library voice must be in the account before TTS."""
    mine = {v['voice_id'] for v in json.loads(api('/v1/voices'))['voices']}
    if vid not in mine:
        owner = json.loads(api(f'/v1/shared-voices?search={VOICES[vid]}&page_size=100'))['voices']
        owner = next(v['public_owner_id'] for v in owner if v['voice_id'] == vid)
        api(f'/v1/voices/add/{owner}/{vid}', {'new_name': f'{VOICES[vid]} (DG Pali test)'})


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        f = f'p{i}.pratham.mp3'
        if not os.path.exists(f'{OUT}/{f}'):
            r = urllib.request.Request('http://127.0.0.1:3011/synthesize', json.dumps({'text': text, 'voice': 'pratham', 'rate': 0.7}).encode(),
                                       {'Content-Type': 'application/json'})
            open(f'{OUT}/{f}', 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(r))['audioContent']))
        vs.append({'id': 'pratham', 'label': 'pratham (DG сейчас)', 'voice': 'pratham', 'file': f, 'sent': text})
        for vid, name in VOICES.items():
            f = f'p{i}.{name}.mp3'
            if not os.path.exists(f'{OUT}/{f}'):
                add_to_library(vid)
                open(f'{OUT}/{f}', 'wb').write(api(f'/v1/text-to-speech/{vid}?output_format=mp3_44100_128',
                                                   {'text': to_script(text), 'model_id': 'eleven_multilingual_v2'}))
            vs.append({'id': name, 'label': f'EL {name}', 'voice': name, 'file': f, 'sent': text})
        phrases.append({'id': f'p{i}', 'text': text, 'ipa': '', 'script': to_script(text), 'variants': vs,
                        'note': '★ лучший; ✓ норм; ✗ плохо. На слово с ошибкой можно нажать'})
        print(i, flush=True)
    json.dump({'round': 'el1', 'title': 'ElevenLabs: голос для пали',
               'intro': 'Шесть голосов ElevenLabs (индийские, модель multilingual v2) читают пали деванагари, и среди них pratham, '
                        'как сейчас в DG (0.7x). Вслепую, сложные места. Оценивайте, понятно ли и правильно ли; лучший станет '
                        'основой нового голоса.',
               'sections': [{'id': 'p', 'title': 'Пали: сложные места', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
