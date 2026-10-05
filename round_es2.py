"""espeak-ng `pi`, second pass after the owner's es1 notes: espeak's own sound fixed (level comma tune, stress barely
lengthens, tap r, affricate j, fricative v; the IPA is unchanged). Words that failed in es1 + all of SN 56.11.
Where es1 had a complaint, the old espeak take is kept next to the new one.
Usage: .venv/bin/python round_es2.py -> out/es2/; then build_page.py with ROUND = 'es2'
"""
import json
import os

from piper import PiperVoice

from round_es1 import SN, WORDS, neural, speak

OUT = 'out/es2'
FAILED = [4, 10, 11, 19, 20]  # es1 words rated bad or commented on
NOTES = {'w4': 'янам, а не ньянаṁ', 'w10': 'r как английская', 'w11': 'r картавая', 'w19': 'тянет у, не тянет о',
         'w20': 'в конце «сун»', 's0_2': 'двойные отрывисто', 's0_3': 'двойные отрывисто', 's1_2': 'r английская',
         's2_2': 'dve тянет', 's3_1': 'sā восходящим тоном', 's3_2': 'странная r', 's3_3': 'странное j',
         's4_1': 'ṁ не читает', 's4_2': 'двойные отрывисто', 's4_4': 'r английская', 's4_5': 'странная ṇ',
         's4_6': 'r немецкая', 's4_7': 'r немецкая', 's4_8': 'r немецкая', 's5_1': 'me восходящим тоном',
         's5_2': 'me восходящим тоном', 's6_1': 'me восходящим тоном', 's6_2': 'me восходящим тоном',
         's12_2': 'ма вместо ва', 's12_3': 'j неправильно', 's12_4': 'ма вместо ва', 's12_5': 'j странно',
         's12_9': 'r английская', 's12_10': 'сун в конце', 's12_11': 'ма вместо ва', 's14_1': 'уданЕЕси',
         's14_2': 'bho восходящим тоном'}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    voices = [('pr', 'pratham по фонемам espeak', PiperVoice.load('models/hi_IN-pratham-medium.onnx'), 1.15),
              ('dg', 'свой голос по фонемам espeak', PiperVoice.load('models/pali_dg-medium.onnx'), 1.0)]
    sutta = [(k.split(':')[1], v.strip()) for k, v in json.load(open(SN, encoding='utf-8')).items() if v.strip()]
    sections = []
    for sid, title, items in [('w', 'Слова, где в es1 была ошибка', [(n, WORDS[n]) for n in FAILED]),
                              ('s', 'SN 56.11 целиком', sutta)]:
        phrases = []
        for n, text in items:
            pid = f'{sid}{n}'.replace('.', '_')
            ipa = speak(text, f'{OUT}/{pid}.mp3')
            vs = [{'id': 'es', 'label': 'espeak-ng pi, исправленный', 'file': f'{pid}.mp3'}]
            if pid in NOTES:
                speak_old = f'../es1/{pid}.mp3'  # es1's take of the same line, before the fixes
                vs.append({'id': 'es-old', 'label': 'espeak-ng pi, как было (es1)', 'file': speak_old})
            for vid, label, voice, length in voices:
                neural(voice, ipa, length, f'{OUT}/{pid}.{vid}.mp3')
                vs.append({'id': vid, 'label': label, 'file': f'{pid}.{vid}.mp3'})
            note = (f'в es1: {NOTES[pid]}. ' if pid in NOTES else '') + '✓ правильно / ✗ ошибка; нажми на неправильное слово'
            phrases.append({'id': pid, 'text': text, 'ipa': ipa, 'script': '', 'note': note, 'variants': vs})
        sections.append({'id': sid, 'title': title, 'multi_best': True, 'phrases': phrases})
    json.dump({'round': 'es2', 'sections': sections}, open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(sum(len(s['phrases']) for s in sections), 'lines')
