"""web/pali-tts.js must read exactly as pali_ipa.py: every segment of the Pali canon through both, no difference allowed.
Run after any change to pali_ipa.py or web/pali-tts.js (the pre-commit hook does). Usage: python check_js.py [max_segments]
"""
import glob
import json
import subprocess
import sys

from pali_ipa import export, to_ipa, tune

ROOT = '/var/www/html/suttacentral.net/sc-data/sc_bilara_data/root/pli/ms'
NODE = '''
import { makePali } from './web/pali-tts.js';
import { readFileSync } from 'fs';
const [data, lines] = JSON.parse(readFileSync(0, 'utf8'));
const p = makePali(data);
console.log(JSON.stringify(lines.map(t => [p.tune(p.toIpa(t, { fullA: true })), p.toIpa(t, { stress: false, finalM: true })])));
'''

if __name__ == '__main__':
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
