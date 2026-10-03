"""Round 13: the owner's own fine-tuned voice (three checkpoints) against Piper pratham with our rules, blind.

The own voice was trained on plain to_ipa(full_a=True) phonemes, so it gets exactly those (no pratham tune()).
Usage: .venv/bin/python round13.py -> out/r13/*.mp3, out/r13/index.json (needs out/export/out/*.onnx)
"""
import json
import os
import subprocess

import numpy as np
from piper import PiperVoice, SynthesisConfig

from pali_ipa import to_ipa, tune

OUT = 'out/r13'
EXP = 'out/export/out'
TEXTS = [
    'Evaṁ me sutaṁ — ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.',
    'Dhammacakkappavattanasutta. Paccattaṁ veditabbo viññūhi.',
    'Cakkhukaraṇī ñāṇakaraṇī upasamāya abhiññāya sambodhāya nibbānāya saṁvattati.',
    'Idha bhikkhu vivicceva kāmehi vivicca akusalehi dhammehi savitakkaṁ savicāraṁ vivekajaṁ pītisukhaṁ paṭhamaṁ jhānaṁ upasampajja viharati.',
    'Jātipaccayā jarāmaraṇaṁ sokaparidevadukkhadomanassupāyāsā sambhavanti. Cakkhusamphassapaccayā vedanā.',
    'Manopubbaṅgamā dhammā, manoseṭṭhā manomayā; manasā ce paduṭṭhena, bhāsati vā karoti vā.',
]
# (id, label, model, own voice?, length_scale): pratham at the reader's default pace (rate 0.7), own voice
# at its recorded pace
VOICES = [('e299', 'свой голос, эпоха 299 (лучшая по валидации)', f'{EXP}/pali_dg-e299.onnx', True, 1.0),
          ('e327', 'свой голос, эпоха 327 (последняя)', f'{EXP}/pali_dg-e327_last.onnx', True, 1.0),
          ('e179', 'свой голос, эпоха 179 (ранняя)', f'{EXP}/pali_dg-e179.onnx', True, 1.0),
          ('pratham', 'Piper pratham + наши правила (сейчас на сайте)', 'models/hi_IN-pratham-medium.onnx', False,
           1.15 / 0.875)]
os.makedirs(OUT, exist_ok=True)
loaded = {vid: PiperVoice.load(m, config_path=f'{EXP}/pali_dg-medium.onnx.json' if own else None)
          for vid, _, m, own, _ in VOICES}
phrases = []
for n, text in enumerate(TEXTS):
    vs = []
    for vid, label, _, own, length in VOICES:
        f = f'{OUT}/p{n}.{vid}.mp3'
        v = loaded[vid]
        cfg = SynthesisConfig(length_scale=length, noise_scale=0.6, noise_w_scale=0.7)
        parts = []
        for sent in [s for s in text.replace('. ', '.\n').split('\n') if s]:
            ipa = to_ipa(sent, full_a=True) if own else tune(to_ipa(sent, full_a=True))
            parts += [v.phoneme_ids_to_audio(v.phonemes_to_ids(list(ipa)), cfg), np.zeros(8000, dtype=np.float32)]
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(v.config.sample_rate), '-ac', '1',
                        '-i', '-', '-b:a', '64k', f], input=np.concatenate(parts).tobytes(), check=True)
        vs.append({'id': vid, 'label': label, 'file': os.path.basename(f), 'sent': ''})
    phrases.append({'id': f'p{n}', 'text': text, 'note': '★ лучший голос; ✗ где слышна ошибка или артефакт',
                    'ipa': to_ipa(text, full_a=True), 'script': '', 'variants': vs})
    print(n, flush=True)
json.dump({'round': 'r13', 'sections': [{'id': 'own', 'title': 'Свой голос против pratham', 'multi_best': False,
                                          'phrases': phrases}]}, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
