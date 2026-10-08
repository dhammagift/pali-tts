"""Round 37: sherpa-onnx (branch remove-espeak, no espeak; our lexicon-pi.txt from the whole canon) against our server,
the same voice (pratham) and the same phonemes - only the engine differs. 15 hard AND common stock phrases
(samphassa, j/jj, ñ/ññ/ñj, y, aspirates, retroflexes, ṁ before consonants, long compounds, vowel hiatus, …pe…).
0.7x for both (length 1.15/0.7), noise 0.6 / 0.7; sherpa with silence-scale 1 (its default 0.2 shortens pauses).
sherpa gets the text cleaned the way our server reads it (quotes -> space, dashes -> comma), so its tokenizer's
punctuation bug (“word / word— skipped) is not what is compared. One take each, blind A/B.
Usage (on f3): .venv/bin/python round37.py -> out/r37/ (+ out/r37/report.txt); then build_page.py with ROUND = 'r37'
Needs the server on :3011 and the sherpa build in /root/sherpa-pi (see vits-piper-pi-pratham/README.md there).
"""
import base64
import json
import os
import re
import subprocess
import unicodedata
import urllib.request

from pali_ipa import to_ipa, tune

OUT = 'out/r37'
# Owner: hard AND common. Stock formulas repeated across hundreds of suttas, each covering several risky words
# (frequent forms with samphassa/mph, j/jj/ñj, y between vowels, aspirates, retroflexes, ṁ + consonant, hiatus,
# long compounds); the exact text is the most repeated variant of the segment in the sutta piṭaka.
PHRASES = [
    ('an1.1:1.1–1.2', 'Evaṁ me sutaṁ—ekaṁ samayaṁ bhagavā sāvatthiyaṁ viharati jetavane anāthapiṇḍikassa ārāme.'),
    ('sn22.82:2.1', 'Atha kho aññataro bhikkhu uṭṭhāyāsanā ekaṁsaṁ uttarāsaṅgaṁ karitvā yena bhagavā tenañjaliṁ paṇāmetvā bhagavantaṁ etadavoca:'),
    ('an9.40:5.7', 'vivicceva kāmehi vivicca akusalehi dhammehi savitakkaṁ savicāraṁ vivekajaṁ pītisukhaṁ paṭhamaṁ jhānaṁ upasampajja viharati.'),
    ('an5.14:5.3', 'vitakkavicārānaṁ vūpasamā ajjhattaṁ sampasādanaṁ cetaso ekodibhāvaṁ avitakkaṁ avicāraṁ samādhijaṁ pītisukhaṁ dutiyaṁ jhānaṁ upasampajja viharati;'),
    ('mn10:3.2', 'Idha, bhikkhave, bhikkhu kāye kāyānupassī viharati ātāpī sampajāno satimā, vineyya loke abhijjhādomanassaṁ;'),
    ('dn22:2.3–2.4', 'So satova assasati, satova passasati. Dīghaṁ vā assasanto ‘dīghaṁ assasāmī’ti pajānāti, dīghaṁ vā passasanto ‘dīghaṁ passasāmī’ti pajānāti;'),
    ('sn12.43:2.2', 'Cakkhuñca paṭicca rūpe ca uppajjati cakkhuviññāṇaṁ. Tiṇṇaṁ saṅgati phasso.'),
    ('mn38:30.5', 'Yā vedanāsu nandī tadupādānaṁ, tassupādānapaccayā bhavo, bhavapaccayā jāti, jātipaccayā jarāmaraṇaṁ sokaparidevadukkhadomanassupāyāsā sambhavanti.'),
    ('dn33:2.2.13', 'cakkhusamphassajā vedanā, sotasamphassajā vedanā, ghānasamphassajā vedanā, jivhāsamphassajā vedanā, kāyasamphassajā vedanā, manosamphassajā vedanā.'),
    ('sn35.62:12.1', '“Yampidaṁ cakkhusamphassapaccayā uppajjati vedayitaṁ sukhaṁ vā dukkhaṁ vā adukkhamasukhaṁ vā tampi niccaṁ vā aniccaṁ vā”ti?'),
    ('mn35:4.3', '“rūpaṁ, bhikkhave, aniccaṁ, vedanā aniccā, saññā aniccā, saṅkhārā aniccā, viññāṇaṁ aniccaṁ.'),
    ('an3.86:5.6', 'So āsavānaṁ khayā anāsavaṁ cetovimuttiṁ paññāvimuttiṁ diṭṭheva dhamme sayaṁ abhiññā sacchikatvā upasampajja viharati.'),
    ('sn48.45:2.3', '‘khīṇā jāti, vusitaṁ brahmacariyaṁ, kataṁ karaṇīyaṁ, nāparaṁ itthattāyā’ti pajānāmīti.'),
    ('snp3.7:1.6', '‘itipi so bhagavā arahaṁ sammāsambuddho vijjācaraṇasampanno sugato lokavidū anuttaro purisadammasārathi satthā devamanussānaṁ buddho bhagavā’ti.'),
    ('sn56.60:2.1', 'Tasmātiha, bhikkhave, ‘idaṁ dukkhan’ti yogo karaṇīyo …pe… ‘ayaṁ dukkhanirodhagāminī paṭipadā’ti yogo karaṇīyo”ti.'),
]
# words reported with the number of suttas they occur in (sutta piṭaka, one file = one sutta)
SUTTA_FREQ = '/root/sherpa-pi/sutta_nd.json'
SHERPA = '/root/sherpa-pi/sherpa-onnx/build/bin/sherpa-onnx-offline-tts'
PKG = '/root/sherpa-pi/vits-piper-pi-pratham'
RATE = 0.7
SENTENCE = re.compile(r'(?<=[.?!;:])\s+')   # tts_server.py


def clean(t):
    """The text as our server's to_ipa() sees it: any non-letter is a word break, dashes and … are pauses."""
    t = unicodedata.normalize('NFC', t).replace('…pe…', '\0').replace('…pa…', '\0')
    t = re.sub(r'[—–…]', ', ', t)
    t = re.sub(r'[^\w\s,;:.?!\0]', ' ', t).replace('\0', ' …pe… ')
    t = re.sub(r'\s+([,;:.?!])', r'\1', re.sub(r'\s+', ' ', t))
    return re.sub(r'([,;:.?!])(?=[,;:.?!])', '', t).strip(' ,;:')


def server_mp3(text, f):
    req = urllib.request.Request('http://127.0.0.1:3011/synthesize', headers={'Content-Type': 'application/json'},
                                 data=json.dumps({'text': text, 'voice': 'pratham', 'rate': RATE}).encode())
    open(f, 'wb').write(base64.b64decode(json.load(urllib.request.urlopen(req))['audioContent']))


def sherpa_mp3(text, f):
    wav = f[:-4] + '.wav'
    log = subprocess.run([SHERPA, f'--vits-model={PKG}/pi-pratham-medium.onnx', f'--vits-tokens={PKG}/tokens.txt',
                          f'--vits-lexicon={PKG}/lexicon-pi.txt', f'--vits-length-scale={1.15 / RATE}',
                          '--vits-noise-scale=0.6', '--vits-noise-scale-w=0.7', '--tts-silence-scale=1', '--debug=1',
                          f'--output-filename={wav}', text], capture_output=True, text=True, check=True).stderr
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-q:a', '7', f], check=True)
    os.remove(wav)
    return (re.findall(r"OOV word skipped: '(.*)'", log),
            ' '.join(re.findall(r"phonemes='(.*)'", log)))


def dur(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                capture_output=True, text=True).stdout)


if __name__ == '__main__':
    nd = json.load(open(SUTTA_FREQ, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    norm = lambda x: re.sub(r'[ ,;:.?!]+', ' ', x).strip()
    phrases, report = [], []
    for i, (sid, text) in enumerate(PHRASES):
        ours = ' '.join(s for s in (tune(to_ipa(x, full_a=True)) for x in SENTENCE.split(text.strip())) if s.strip(' ,.?!'))
        server_mp3(text, f'{OUT}/p{i}.server.mp3')
        oov, sph = sherpa_mp3(clean(text), f'{OUT}/p{i}.sherpa.mp3')
        same = norm(ours) == norm(sph)
        d_s, d_o = dur(f'{OUT}/p{i}.sherpa.mp3'), dur(f'{OUT}/p{i}.server.mp3')
        ws = sorted(set(re.findall(r'[a-zāīūṭḍṅñṇḷṁ]+', text.lower())), key=lambda w: -nd.get(w, 0))
        report.append(f'p{i} {sid} | ' + ' '.join(f'{w}:{nd.get(w, 0)}' for w in ws[:8]))
        report.append(f'   same phones {same}; OOV {oov}; sherpa {d_s:.2f}s, server {d_o:.2f}s ({d_s - d_o:+.2f})'
                      + ('' if same else f'\n   sherpa: {sph}\n   server: {ours}'))
        vs = [{'id': 'sherpa', 'label': 'sherpa-onnx + наш словарь', 'file': f'p{i}.sherpa.mp3', 'sent': sph},
              {'id': 'server', 'label': 'наш сервер (r28)', 'file': f'p{i}.server.mp3', 'sent': ours}]
        phrases.append({'id': f'p{i}', 'text': text, 'ipa': ours, 'script': '', 'variants': vs,
                        'note': '✓ норм, ✗ плохо; нажми на слово, где звучит иначе или хуже'})
    json.dump({'round': 'r37', 'sections': [{'id': 'p', 'title': 'sherpa-onnx против нашего сервера, 0.7x', 'multi_best': False,
                                             'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(f'{OUT}/report.txt', 'w', encoding='utf-8').write('\n'.join(report) + '\n')
    print('\n'.join(report))
