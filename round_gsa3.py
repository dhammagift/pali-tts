"""Round gsa3 (owner 2026-11-17: «двойные как-то сокращает», puggalā strange): the Google-trained pratham with the fixes
so far (round_gsa2.fixes: final a/i/u long, intervocalic h long) against the same plus double consonants long (kk -> kːk)
and ariya with a long i (round_gsa2.fixes2). SN 56.11 / SN 12.2 / AN lines full of doubles. Blind A/B/C; C also plain i for ɪ (owner: piyo «пыйо»).
Usage: round_gsa3.py build"""
import json
import os
import subprocess
import sys
import wave

sys.path.insert(0, '/root/gsa/texts')
from pali_ipa import to_ipa  # noqa: E402
from piper import PiperVoice  # noqa: E402
from piper.config import SynthesisConfig  # noqa: E402
from round_gsa2 import MODEL, fixes, fixes3  # noqa: E402

OUT = 'out/gsa3'
TEXTS = [
    ('sn56.11:2.1', 'Dveme, bhikkhave, antā pabbajitena na sevitabbā.'),
    ('sn56.11:2.4', 'Ete kho, bhikkhave, ubho ante anupagamma majjhimā paṭipadā tathāgatena abhisambuddhā.'),
    ('sn56.11:3.3', 'Sammādiṭṭhi sammāsaṅkappo sammāvācā sammākammanto sammāājīvo sammāvāyāmo sammāsati sammāsamādhi.'),
    ('sn56.11:4.1', 'Idaṁ kho pana, bhikkhave, dukkhaṁ ariyasaccaṁ.'),
    ('sn56.11:5.1', 'Pubbe ananussutesu dhammesu cakkhuṁ udapādi, ñāṇaṁ udapādi, paññā udapādi, vijjā udapādi, āloko udapādi.'),
    ('sn12.2:3.2', 'Yā tesaṁ tesaṁ sattānaṁ tamhi tamhi sattanikāye jarā jīraṇatā khaṇḍiccaṁ pāliccaṁ valittacatā.'),
    ('sn22.87:3.2', 'Yo kho, vakkali, dhammaṁ passati so maṁ passati.'),
    ('an4.85', 'Cattārome, bhikkhave, puggalā santo saṁvijjamānā lokasmiṁ.'),
    ('an5.250:3.3', 'Yo kho myāyaṁ puggalo piyo manāpo so kālaṅkato.'),
    ('sn47.6:4.3', 'Ko ca, bhikkhave, bhikkhuno gocaro sako pettiko visayo?'),
]
VARIANTS = {'now': ('как сейчас', fixes), 'mild': ('двойные полудолгие + ariya', fixes3),
            # owner on gsa2: piyo «пыйо», visayo «высайо» - the short ɪ sounds like ы; plain i instead
            'mild_i': ('двойные полудолгие + ariya + чистое и', lambda s: fixes3(s).replace('ɪ', 'i'))}

if __name__ == '__main__' and sys.argv[1:] == ['build']:
    os.makedirs(OUT, exist_ok=True)
    voice = PiperVoice.load(MODEL, config_path=MODEL + '.json')
    cfg = SynthesisConfig(length_scale=1.15, noise_scale=0.6, noise_w_scale=0.7)
    phrases = []
    for i, (seg, text) in enumerate(TEXTS):
        vs = []
        for vid, (label, f) in VARIANTS.items():
            ipa = f(to_ipa(text, full_a=True))
            a = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), cfg)
            wav = f'{OUT}/p{i:02d}.{vid}.wav'
            with wave.open(wav, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                w.writeframes((a.clip(-1, 1) * 32767).astype('int16').tobytes())
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-q:a', '5', wav[:-4] + '.mp3'], check=True)
            os.remove(wav)
            vs.append({'id': vid, 'label': label, 'file': f'p{i:02d}.{vid}.mp3', 'sent': ipa})
        phrases.append({'id': f'p{i:02d}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'{seg}. Слушайте двойные согласные (bhikkhave, sammā, passati, puggalā), ariya и «и» (piyo, visayo). ★ лучший; ✓ правильно; ✗ неправильно'})
    json.dump({'round': 'gsa3', 'title': 'Новый голос: двойные согласные',
               'intro': 'Новый голос с фиксами pana/tena и sahagatā. В каждой фразе '
                        'три варианта вслепую: как сейчас; двойные согласные чуть удлинены (bhikkhave, sammā, passati) и ariya с долгим i; '
                        'то же плюс чистое «и» вместо «ы» (piyo, visayo). Какой правильнее?',
               'sections': [{'id': 'p', 'title': 'Двойные согласные', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
