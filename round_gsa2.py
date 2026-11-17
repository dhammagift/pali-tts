"""Round gsa2 (owner 2026-11-17): the Google-trained pratham (gsa run 2) says a word-final o like u (kho, so, puriso: the
Hindi recogniser heard u in 11% of final o over 200 canon lines, where Google's own reading had o). Short canon lines full
of final o, three ways of feeding it, blind: as now / long final o (the owner's Google fix in memo.js, ो -> ोो) / open o.
All three carry the fixes that worked: word-final a/i/u long (memo.js, pana not pan), intervocalic h long (sahagatā).
Usage: round_gsa2.py build"""
import json
import os
import re
import subprocess
import sys
import wave

sys.path.insert(0, '/root/gsa/texts')
from pali_ipa import to_ipa  # noqa: E402
from piper import PiperVoice  # noqa: E402
from piper.config import SynthesisConfig  # noqa: E402

OUT = 'out/gsa2'
MODEL = '/root/gsa/train-run2/out/out/pali_gsa-medium.onnx'
TEXTS = [  # (segment, text)
    ('mn43:36.1', 'Rāgo kho, āvuso, kiñcano, doso kiñcano, moho kiñcano.'),
    ('an5.250:3.3', 'Yo kho myāyaṁ puggalo piyo manāpo so kālaṅkato.'),
    ('sn22.84:9.2', 'Eko puriso amaggakusalo, eko puriso maggakusalo.'),
    ('dn25:23.4', 'Yo eva vo ācariyo, so eva vo ācariyo hotu.'),
    ('sn47.6:4.3', 'Ko ca, bhikkhave, bhikkhuno gocaro sako pettiko visayo?'),
    ('dn10:1.30.4', 'So cāyaṁ, bho ānanda, ariyo sīlakkhandho paripuṇṇo, no aparipuṇṇo.'),
    ('sn38.1:2.3', 'Yo kho, āvuso, rāgakkhayo dosakkhayo mohakkhayo.'),
    ('mn75:10.6', 'Eko vassiko, eko hemantiko, eko gimhiko.'),
]
B = r'(?=[\s,.;:?!]|$)'
VOW = 'aʌɪiʊueoː'
IH = re.compile(f'(?<=[{VOW}])(ˈ?)h(ˈ?)(?=[{VOW}])')


def fixes(ipa):
    ipa = re.sub('ʌ' + B, 'aː', ipa)
    ipa = re.sub('ɪ' + B, 'iː', ipa)
    ipa = re.sub('ʊ' + B, 'uː', ipa)
    return IH.sub(lambda m: m.group(1) + 'hh' + m.group(2), ipa)


GEM = re.compile('([pbtdʈɖkɡcɟmnɳɲŋlɭsʋjɾ])(?=\\1)')


def fixes2(ipa):
    # gsa3: double consonants long (kk -> kːk: the voice says bhikhave, pasati - Google shortens them too) and ariya with
    # a long i (ariyasaccaṁ came out «аресаччам»); the Hindi recogniser hears both fixed in 6 lines of SN 56.11
    return GEM.sub(r'\1ː', fixes(ipa)).replace('ɾɪjʌ', 'ɾiːjʌ')


def fixes3(ipa):
    # owner on gsa3: kːk is overdone («слишком утрированно»): half-long first consonant (ˑ) - the recogniser still hears
    # sammā, passati, pabba, bhikkhave double; half-long on stops only lost sammā and passati
    return GEM.sub(r'\1ˑ', fixes(ipa)).replace('ɾɪjʌ', 'ɾiːjʌ')


VARIANTS = {
    'now': ('как сейчас', lambda s: s),
    'long_o': ('долгое конечное o', lambda s: re.sub('oː' + B, 'oːo', s)),
    'open_o': ('открытое конечное o', lambda s: re.sub('oː' + B, 'ɔː', s)),
}

if __name__ == '__main__' and sys.argv[1:] == ['build']:
    os.makedirs(OUT, exist_ok=True)
    voice = PiperVoice.load(MODEL, config_path=MODEL + '.json')
    cfg = SynthesisConfig(length_scale=1.15, noise_scale=0.6, noise_w_scale=0.7)
    phrases = []
    for i, (seg, text) in enumerate(TEXTS):
        vs = []
        for vid, (label, f) in VARIANTS.items():
            ipa = f(fixes(to_ipa(text, full_a=True)))
            a = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(list(ipa)), cfg)
            wav = f'{OUT}/p{i:02d}.{vid}.wav'
            with wave.open(wav, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                w.writeframes((a.clip(-1, 1) * 32767).astype('int16').tobytes())
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-q:a', '5', wav[:-4] + '.mp3'], check=True)
            os.remove(wav)
            vs.append({'id': vid, 'label': label, 'file': f'p{i:02d}.{vid}.mp3', 'sent': ipa})
        phrases.append({'id': f'p{i:02d}', 'text': text, 'ipa': '', 'script': '', 'variants': vs,
                        'note': f'{seg}. Слушайте конец слов на -o (kho, so, yo, eko…): «о», а не «у». ★ лучший; ✓ правильно; ✗ неправильно'})
    json.dump({'round': 'gsa2', 'title': 'Новый голос: конечное o',
               'intro': 'Новый голос (pratham, обученный на чтении Google) с фиксами pana/tena и sahagatā. '
                        'В каждой фразе три варианта вслепую; отличаются только конечным o. Какой читает «о», а не «у»?',
               'sections': [{'id': 'p', 'title': 'Конечное o', 'multi_best': False, 'phrases': phrases}]},
              open(f'{OUT}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ok', len(phrases))
