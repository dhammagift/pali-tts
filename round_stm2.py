"""Round stm2: which Supertonic M1 student stays (owner 2026-10-16: «вряд ли нужно оставлять оба… давай решим»):
A (2:30) vs B (12:30) on 6 hard SuttaCentral lines (каково / таково / таковым, ё, a question, names, a long line),
blind, next to the teacher (M1) and the Russian voices DG has now. Piper voices through the local tts_server, as DG
reads them (pieces, gain); M1 as in st1.
Usage (on f3): /root/venv-ml/bin/python round_stm2.py -> out/stm2/; then build_page.py with ROUND = 'stm2'
"""
import json
import os

from round_st1 import ST, load_text_to_speech, load_voice_style, mp3, piper

OUT = 'out/stm2'
TEXTS = ['Каков будет его будущий удел? Каково его будущее направление?»',
         'Поскольку он считает всё это таковым, он не волнуется о том, чего не существует.',
         'Таково пятое знание, обретённое им, благородное, сверхмирское, которого не имеют обычные заурядные люди.',
         '«Видишь, почтенный, какой огромной силой и могуществом обладаю я?»',
         '«Точно так же, Маханама, благородный ученик, наделённый этими четырьмя вещами, склоняется, устремляется, '
         'направляется к ниббане».',
         'По мере того как он ходил от дома к дому в Саваттхи, собирая подаяния, он увидел некую женщину в родовых '
         'муках, с болезненными родами.']
PIPER = [('stm1a', 'ученик M1 · A (2:30)'), ('stm1b', 'ученик M1 · B (12:30)'), ('dgru', 'o Dhamma.Gift (dgru)'),
         ('ruslan', 'ruslan (сейчас)')]

if __name__ == '__main__':
    tts = load_text_to_speech(f'{ST}/assets/onnx')
    m1 = load_voice_style([f'{ST}/assets/voice_styles/M1.json'])
    os.makedirs(OUT, exist_ok=True)
    phrases = []
    for i, text in enumerate(TEXTS):
        vs = []
        for vid, label in PIPER:
            piper(text, vid, f'{OUT}/ru{i}.{vid}.mp3')
            vs.append({'id': vid, 'label': label, 'file': f'ru{i}.{vid}.mp3', 'sent': text})
        wav, dur = tts(text, 'ru', m1, 8, 1.05)
        mp3(wav.reshape(-1)[:int(tts.sample_rate * dur[0])], tts.sample_rate, f'{OUT}/ru{i}.m1.mp3')
        vs.append({'id': 'm1', 'label': 'M1 — учитель (Supertonic)', 'file': f'ru{i}.m1.mp3', 'sent': text})
        phrases.append({'id': f'ru{i}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': '★ лучший; ok — годится; ✗ — плохо (ударение, шум, металл, монотонно). Слово с ошибкой — кликни по нему'})
    json.dump({'round': 'stm2', 'sections': [{'id': 'ru', 'title': 'Русский: сложные фразы, вслепую', 'multi_best': False,
                                              'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
