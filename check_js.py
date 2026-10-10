"""web/pali-tts.js must read exactly as pali_ipa.py: every segment of the Pali canon through both, no difference allowed.
Run after any change to pali_ipa.py or web/pali-tts.js (the pre-commit hook does). Usage: python check_js.py [max_segments]
--tr [max_segments]: the same for the en/ru voices - SuttaCentral translations through tts_server's phonemes (respell.py +
piper's espeak) and through pali-tts.js + web/espeak (needs piper, the voices' models and a built web/espeak).
"""
import glob
import json
import os
import subprocess
import sys

from pali_ipa import export, to_ipa, tune

TR = os.environ.get('SC_TR', '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/translation')  # f3: a copy

ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms'
NODE = '''
import { makePali } from './web/pali-tts.js';
import { readFileSync } from 'fs';
const [data, lines] = JSON.parse(readFileSync(0, 'utf8'));
const p = makePali(data);
console.log(JSON.stringify(lines.map(t => [p.tune(p.toIpa(t, { fullA: true })), p.toIpa(t, { stress: false, finalM: true })])));
'''

NODE_TR = '''
import { makePali, loadEspeak, makeTranslation } from './web/pali-tts.js';
import make from './web/espeak/espeak.mjs';
import { readFileSync } from 'fs';
const [data, rdata, files, jobs] = JSON.parse(readFileSync(0, 'utf8'));
const es = await loadEspeak(make, Object.fromEntries(Object.entries(files).map(([k, v]) => [k, readFileSync(v)])));
const t = makeTranslation(rdata, makePali(data), es);
console.log(JSON.stringify(jobs.map(([lang, voice, idMap, sents]) => sents.map(s => t.phonemes(lang, voice, idMap, s)))));
'''
# one voice per espeak voice of tts_server's VOICES (irina reads like ruslan)
TR_VOICES = [('en_GB-alan-medium', 'en'), ('en_US-norman-medium', 'en'), ('en_US-kathleen-low', 'en'), ('ru_RU-ruslan-medium', 'ru')]
ESPEAK_FILES = ['phontab', 'phonindex', 'phondata', 'intonations', 'en_dict', 'ru_dict', 'lang/gmw/en', 'lang/gmw/en-GB-x-rp',
                'lang/gmw/en-US', 'lang/zle/ru']


def check_translations(n):
    import re
    import piper
    from piper import PiperVoice
    from respell import en_phonemes, ru_phonemes, export as respell_export
    data_dir = os.path.join(os.path.dirname(piper.__file__), 'espeak-ng-data')
    sentence = re.compile(r'(?<=[.?!;:])\s+')
    jobs, py = [], []
    for model, lang in TR_VOICES:
        lines = []
        for f in sorted(glob.glob(f'{TR}/{lang}/**/*.json', recursive=True)):
            if '/blurb/' in f or '/site/' in f or '/name/' in f:
                continue
            lines += [t.strip() for t in json.load(open(f, encoding='utf-8')).values() if isinstance(t, str) and t.strip()]
        lines = list(dict.fromkeys(lines))[:n]
        voice = PiperVoice.load(f'models/{model}.onnx')
        sents = [s for t in lines for s in sentence.split(t)]
        py.append([[p for p in [en_phonemes(voice, s)] if p] if lang == 'en' else [p for p in ru_phonemes(voice, s) if p]
                   for s in sents])
        jobs.append([lang, voice.config.espeak_voice, voice.config.phoneme_id_map, sents])
    files = {f: os.path.join(data_dir, f) for f in ESPEAK_FILES}
    js = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE_TR], input=json.dumps([export(), respell_export(), files, jobs]),
                                   capture_output=True, text=True, check=True).stdout)
    bad = 0
    for (lang, voice, _, sents), a, b in zip(jobs, py, js):
        diff = [(s, x, y) for s, x, y in zip(sents, a, b) if x != y]
        bad += len(diff)
        for s, x, y in diff[:5]:
            print('DIFF', voice, s, '\n  py', [''.join(p) for p in x], '\n  js', [''.join(p) for p in y])
        print(voice, len(sents), 'sentences,', len(diff), 'differ')
    return bad


if __name__ == '__main__':
    if sys.argv[1:2] == ['--tr']:
        sys.exit(1 if check_translations(int(sys.argv[2]) if len(sys.argv) > 2 else None) else 0)
    lines = []
    for f in sorted(glob.glob(f'{ROOT}/**/*.json', recursive=True)):
        lines += [t.strip() for t in json.load(open(f, encoding='utf-8')).values() if t.strip()]
    lines = list(dict.fromkeys(lines))[:int(sys.argv[1]) if len(sys.argv) > 1 else None]
    py = [[tune(to_ipa(t, full_a=True)), to_ipa(t, stress=False, final_m=True)] for t in lines]
    js = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE], input=json.dumps([export(), lines]),
                                   capture_output=True, text=True, check=True).stdout)
    bad = [(t, a, b) for t, a, b in zip(lines, py, js) if a != b]
    for t, a, b in bad[:10]:
        print('DIFF', t, '\n  py', a, '\n  js', b)
    print(len(lines), 'segments,', len(bad), 'differ')
    sys.exit(1 if bad else 0)
