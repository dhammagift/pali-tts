"""Round sa1 (owner 2026-10-23: «что насчёт качественного санскритского TTS?»): Sanskrit voices reading Pali in
Devanagari against pratham with our rules, on the lines fixed last: Idamavoca bhagavā, vimucciṁsūti, pharitvā,
tiṭṭhati, the ordinals. Candidates (postponed 2026-10-03, issue #1): svara-tts-v1 (male, via its HF Space),
AI4Bharat vits_rasa_13 (SAN_M, book style) and Indic Parler-TTS (Aryan), both on f3's CPU, and the owner's Android
Sanskrit voice (his recording of the whole problem list, cut at its pauses; no tiṭṭhati line there).
Blind, one take each, loudness evened. Inputs in out/sa/ (lN.<voice>.wav, lN.pratham.mp3); usage:
python3 round_sa1.py -> out/sa1/; then build_page.py with ROUND = 'sa1'
"""
import json
import os
import random
import subprocess

OUT, SRC = 'out/sa1', 'out/sa'
TEXTS = ['Idamavoca bhagavā.',
         'Imasmiñca pana veyyākaraṇasmiṁ bhaññamāne tassa bhikkhusahassassa anupādāya āsavehi cittāni vimucciṁsūti.',
         'Mettāsahagatena cetasā ekaṁ disaṁ pharitvā viharati.',
         'Itthirūpaṁ, bhikkhave, purisassa cittaṁ pariyādāya tiṭṭhatī”ti.',
         'Paṭhamaṁ. Dutiyaṁ. Tatiyaṁ. Catutthaṁ. Pañcamaṁ.']
VOICES = ['pratham', 'svara_male', 'rasa_book', 'parler_aryan', 'android']

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs, letters = [], random.Random(f'sa1-{i}').sample('abcde', 5)  # blind: letters shuffled per line
        for k, v in enumerate(VOICES):
            src = next((f'{SRC}/l{i}.{v}.{e}' for e in ('wav', 'mp3') if os.path.exists(f'{SRC}/l{i}.{v}.{e}')), None)
            if not src:
                continue
            vid = letters[k]
            subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', src, '-ac', '1', '-af', 'loudnorm=I=-18:TP=-1.5',
                            '-q:a', '5', f'{OUT}/l{i}.{vid}.mp3'], check=True)
            vs.append({'id': vid, 'label': vid.upper(), 'voice': v, 'file': f'l{i}.{vid}.mp3', 'sent': ''})
        phrases.append({'id': f'l{i}', 'text': text, 'ipa': '', 'script': '', 'variants': sorted(vs, key=lambda x: x['id']),
                        'note': '★ лучше всех; ✓ правильно; ✗ неправильно (что слышно)'})
    json.dump({'round': 'sa1', 'sections': [{'id': 'sa', 'title': 'Санскритские голоса против pratham', 'multi_best': False,
                                             'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', sum(len(p['variants']) for p in phrases))
