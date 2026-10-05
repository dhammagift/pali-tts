"""Pali words inside a translation, respelled so an English or Russian Piper voice says them sanely.

The en/ru voices phonemize with espeak, which reads IAST as English/Russian letters (Vārāṇasī,
Tathāgata -> "th" as in "think", phassa -> "f"). Russian: Pali in Latin -> Cyrillic by Pali sound.
English: diacritics off, aspirates folded into plain stops (an English voice can't aspirate on cue).
"""
import re
import unicodedata

from pali_ipa import to_ipa

PALI_CHARS = 'āīūṭḍṅñṇḷṃṁ'
# Pali without diacritics in an English sentence: doubled aspirates, ññ, or an aspirate opening the word
# (bhikkhu, dhamma, khandha). Not "ddh"/"tth": Buddha and Matthew read fine as English.
EN_PALI_HINT = re.compile(r'kkh|ggh|cch|jjh|ṭṭh|bbh|ññ|^(?:bh|dh|kh|gh|jh|ph)(?=[aeiou])')
WORD = re.compile(r"[A-Za-z" + PALI_CHARS + PALI_CHARS.upper() + r"ĀĪŪṬḌṄÑṆḶṂṀ]+")

RU = [  # longest first
    ('kh', 'кх'), ('gh', 'гх'), ('ch', 'чх'), ('jh', 'джх'), ('ṭh', 'тх'), ('ḍh', 'дх'), ('th', 'тх'),
    ('dh', 'дх'), ('ph', 'пх'), ('bh', 'бх'), ('ya', 'я'), ('yā', 'я'), ('yu', 'ю'), ('yū', 'ю'), ('ye', 'е'),
    ('a', 'а'), ('ā', 'а'), ('i', 'и'), ('ī', 'и'), ('u', 'у'), ('ū', 'у'), ('e', 'е'), ('o', 'о'),
    ('k', 'к'), ('g', 'г'), ('ṅ', 'н'), ('c', 'ч'), ('j', 'дж'), ('ñ', 'нь'), ('ṭ', 'т'), ('ḍ', 'д'),
    ('ṇ', 'н'), ('t', 'т'), ('d', 'д'), ('n', 'н'), ('p', 'п'), ('b', 'б'), ('m', 'м'), ('y', 'й'),
    ('r', 'р'), ('l', 'л'), ('ḷ', 'л'), ('v', 'в'), ('s', 'с'), ('h', 'х'), ('ṃ', 'м'), ('ṁ', 'м'),
    ('f', 'ф'), ('w', 'в'), ('z', 'з'), ('q', 'к'), ('x', 'кс'),
]
RU_RX = re.compile('|'.join(re.escape(k) for k, _ in sorted(RU, key=lambda kv: -len(kv[0]))))
RU_MAP = dict(RU)

EN = [('kh', 'k'), ('gh', 'g'), ('ch', 'ch'), ('jh', 'j'), ('ṭh', 't'), ('ḍh', 'd'), ('th', 't'), ('dh', 'd'),
      ('ph', 'p'), ('bh', 'b'), ('ā', 'aa'), ('ī', 'ee'), ('ū', 'oo'), ('c', 'ch'), ('ñ', 'ny'), ('ṅ', 'ng'),
      ('ṭ', 't'), ('ḍ', 'd'), ('ṇ', 'n'), ('ḷ', 'l'), ('ṃ', 'm'), ('ṁ', 'm')]
EN_RX = re.compile('|'.join(re.escape(k) for k, _ in sorted(EN, key=lambda kv: -len(kv[0]))))
EN_MAP = dict(EN)


# Pali words an English text writes without diacritics; a plural "s" is allowed (suttas, bhikkhus)
EN_PALI_WORDS = set('sutta dhamma sangha vinaya nikaya nibbana jhana metta karuna mudita upekkha samadhi vipassana '
                    'samatha sila panna kamma bhikkhu bhikkhuni tathagata arahant arahat dukkha anatta anicca sati '
                    'satipatthana abhidhamma bodhisatta uposatha patimokkha gotama sariputta moggallana ananda '
                    'kassapa jataka devadatta rahula vassa dana khandha nama rupa vedana sanna sankhara vinnana'.split())
# our Pali IPA (espeak-hi symbols) -> what the English voices were trained on: plain stops (an English voice
# can't aspirate on cue), no retroflex, single consonants
EN_IPA = [('kʰ', 'k'), ('ɡʰ', 'ɡ'), ('cʰ', 'tʃ'), ('ɟʰ', 'dʒ'), ('ʈʰ', 't'), ('ɖʰ', 'd'), ('tʰ', 't'),
          ('dʰ', 'd'), ('pʰ', 'p'), ('bʰ', 'b'), ('ɭʰ', 'l'), ('c', 'tʃ'), ('ɟ', 'dʒ'), ('ʈ', 't'), ('ɖ', 'd'),
          ('ɳ', 'n'), ('ɲ', 'nj'), ('ɭ', 'l'), ('ʋ', 'v'), ('ɾ', 'ɹ'), ('aː', 'ɑː'), ('eː', 'eɪ'), ('e', 'ɛ')]
EN_IPA_RX = re.compile('|'.join(re.escape(k) for k, _ in sorted(EN_IPA, key=lambda kv: -len(kv[0]))))


def en_ipa(word, us=False):
    """One Pali word as English-voice phonemes: dhamma -> dˈʌmɐ, sutta -> sˈʊtɐ, Vārāṇasī -> vɑːɹˈɑːnɐsiː."""
    ipa = EN_IPA_RX.sub(lambda m: dict(EN_IPA)[m.group()], to_ipa(word, final_m=True))
    ipa = re.sub(r'oː|o', 'oʊ' if us else 'əʊ', ipa.replace('ə', 'ə' if us else 'ɐ'))
    return re.sub(r'(tʃ|dʒ|[kɡtdpbmnlsvhjɹ])\1', r'\1', ipa)  # geminates: English has none


def is_pali_en(low):
    # Round 16: our phonemes won for the common plain-spelled words (sutta, Dhamma, bhikkhus); for words
    # with diacritics (Vārāṇasī, Nibbāna) the respelling was as good or better, so those stay respelled.
    stem = low[:-1] if low.endswith('s') and low[:-1] in EN_PALI_WORDS else low
    return stem in EN_PALI_WORDS


def en_parts(text, us=False):
    """English text -> [('text', run) | ('ipa', phonemes)]: Pali words get our phonemes, the rest stays for espeak."""
    out, last = [], 0
    for m in WORD.finditer(unicodedata.normalize('NFC', text)):
        low = m.group().lower()
        if not is_pali_en(low):
            continue
        plural = low.endswith('s') and low[:-1] in EN_PALI_WORDS
        if m.start() > last:
            out.append(('text', text[last:m.start()]))
        out.append(('ipa', en_ipa(low[:-1] if plural else low, us) + ('z' if plural else '')))
        last = m.end()
    if last < len(text):
        out.append(('text', text[last:]))
    return out


# Abbreviations of English translations, spelled out: espeak read "Ven." as "ven" plus a sentence-end
# pause, "i.e." as "eye-ee", "SN 56.11" as "es en fifty six point one one" (owner: Ven. Sariputta ->
# Venerable Sariputta and so on).
EN_ABBR = [(re.compile(r'\bVens\.?(?=\s+[A-ZĀĪŪÑ])'), 'Venerables'), (re.compile(r'\bVen\.?(?=\s+[A-ZĀĪŪÑ])'), 'Venerable'),
           (re.compile(r'\bi\.\s?e\.,?'), 'that is,'), (re.compile(r'\be\.\s?g\.,?'), 'for example,'),
           (re.compile(r'\bcf\.'), 'compare'), (re.compile(r'\blit\.'), 'literally'), (re.compile(r'\bSkt\.'), 'Sanskrit')]
EN_BOOKS = {'DN': 'Dīgha Nikāya', 'MN': 'Majjhima Nikāya', 'SN': 'Saṁyutta Nikāya', 'AN': 'Aṅguttara Nikāya',
            'Snp': 'Sutta Nipāta', 'Dhp': 'Dhammapada', 'Ud': 'Udāna', 'Iti': 'Itivuttaka', 'Thag': 'Theragāthā',
            'Thig': 'Therīgāthā', 'Kp': 'Khuddakapāṭha'}
EN_REF = re.compile(r'\b(' + '|'.join(EN_BOOKS) + r')\s?(\d+)(?:\.(\d+))?')


def en_expand(text):
    for rx, full in EN_ABBR:
        text = rx.sub(full, text)
    # "SN 56.11" -> "Saṁyutta Nikāya 56, 11": the book's name, the numbers apart, not "56 point 11"
    return EN_REF.sub(lambda m: f'{EN_BOOKS[m.group(1)]} {m.group(2)}' + (f', {m.group(3)}' if m.group(3) else ''), text)


def en_phonemes(voice, text):
    """Phoneme list for a Piper English voice: espeak for the English runs, our phonemes for the Pali words."""
    text = en_expand(text)
    us = voice.config.espeak_voice == 'en-us'
    seq = []
    for kind, val in en_parts(text, us):
        ph = [p for sent in voice.phonemize(respell(val, 'en')) for p in sent] if kind == 'text' else list(val)
        lead = re.match(r'\s*([,.;:?!])', val) if kind == 'text' else None
        if lead and (not ph or ph[0] != lead.group(1)):  # espeak drops a run's leading punctuation: keep the pause
            ph = [lead.group(1), ' '] + ph
        if ph:
            seq += ([' '] if seq and ph[0] not in ',.?!;:' else []) + ph
    seq = [p for i, p in enumerate(seq) if not (p == ' ' and i and seq[i - 1] == ' ')]
    return [p for p in seq if p in voice.config.phoneme_id_map]


# espeak-ng (issue #1045, open since 2021) leaves some consonants hard before a soft sign: боль = бол,
# день, кровь, только, учитель. т and с it softens itself. Letter -> the phonemes espeak gives it.
RU_SOFTEN = {'л': ('ɭ', 'l'), 'н': ('n',), 'в': ('v', 'f'), 'м': ('m',), 'р': ('r',)}
RU_WORD = re.compile(r'[а-яё]+(?:-[а-яё]+)*')


def ru_soften(word, phonemes):
    """word: one Russian word; phonemes: its phonemes. Adds ʲ after л/н/в/м/р that stand before ь."""
    out = list(phonemes)
    for letter, bases in RU_SOFTEN.items():
        if letter + 'ь' not in word:
            continue
        idx = [i for i, p in enumerate(out) if p in bases]
        letters = [m.start() for m in re.finditer(letter, word)]
        if len(idx) != len(letters):  # can't pair the letters with the phonemes: leave the word as espeak said it
            continue
        for k in reversed(range(len(letters))):
            pos, i = letters[k], idx[k]
            if word[pos + 1:pos + 2] == 'ь' and (i + 1 >= len(out) or out[i + 1] != 'ʲ'):
                out.insert(i + 1, 'ʲ')
    return out


def ru_phonemes(voice, text):
    """Phoneme lists (one per sentence) for a Piper Russian voice, with the soft sign restored."""
    text = respell(text, 'ru')
    words = RU_WORD.findall(text.lower())
    sents = [list(s) for s in voice.phonemize(text) if s]
    flat = [p for s in sents for p in s + [' ']]  # a space between sentences too, or their edge words merge
    tokens, cur = [], []
    for p in flat:  # split into words; punctuation stays inside the token it is glued to
        if p == ' ':
            if cur:
                tokens.append(cur)
            cur = []
        else:
            cur.append(p)
    if len([t for t in tokens if any(c.isalpha() for c in t)]) != len(words):
        return sents  # espeak split the words differently: no fix rather than a wrong one
    fixed, wi = {}, 0
    for ti, t in enumerate(tokens):
        if any(c.isalpha() for c in t):
            if 'ь' in words[wi]:
                fixed[ti] = ru_soften(words[wi], t)
            wi += 1
    out, ti, cur = [], 0, []
    for s in sents:  # put the words back into their sentences
        new, word = [], []
        for p in s + [' ']:
            if p == ' ':
                if word:
                    new += fixed.get(ti, word)
                    ti += 1
                word = []
                new.append(' ')
            else:
                word.append(p)
        out.append(new[:-1])
    return out


def _case(src, out):
    return out[:1].upper() + out[1:] if src[:1].isupper() else out


def respell(text, lang):
    text = unicodedata.normalize('NFC', text)

    def word(m):
        w = m.group()
        low = w.lower()
        if lang == 'ru':
            return _case(w, RU_RX.sub(lambda x: RU_MAP[x.group()], low))  # any Latin word in Russian text
        if lang == 'en' and (any(c in PALI_CHARS for c in low) or EN_PALI_HINT.search(low)):
            return _case(w, EN_RX.sub(lambda x: EN_MAP[x.group()], low))
        return w
    return WORD.sub(word, text) if lang in ('ru', 'en') else text


if __name__ == '__main__':
    assert respell('Благословенный в Vārāṇasī, монахи (bhikkhū).', 'ru') == 'Благословенный в Варанаси, монахи (бхиккху).'
    assert respell('Tathāgata, phassa, Ñāṇa', 'ru') == 'Татхагата, пхасса, Ньана'
    assert respell('The Blessed One in Vārāṇasī dwells; the bhikkhus.', 'en') == 'The Blessed One in Vaaraanasee dwells; the bikkus.'
    assert respell('Tathāgata and phassa', 'en') == 'Tataagata and passa', respell('Tathāgata and phassa', 'en')
    assert respell('the thing that the Buddha said, abhorred', 'en') == 'the thing that the Buddha said, abhorred'  # English untouched
    assert respell('the Dhamma and dukkha', 'en') == 'the Damma and dukka'
    assert en_ipa('dhamma') == 'dˈʌmɐ', en_ipa('dhamma')
    assert en_ipa('sutta') == 'sˈʊtɐ', en_ipa('sutta')
    assert en_ipa('gotamo') == 'ɡˈəʊtɐməʊ', en_ipa('gotamo')
    assert en_parts('the suttas, monks') == [('text', 'the '), ('ipa', 'sˈʊtɐz'), ('text', ', monks')], en_parts('the suttas, monks')
    assert [k for k, _ in en_parts('in Vārāṇasī the Dhamma')] == ['text', 'ipa']  # diacritics: respelled
    assert en_expand('There Ven. Sāriputta said, i.e. the Buddha (SN 56.11; MN 10).') == \
        'There Venerable Sāriputta said, that is, the Buddha (Saṁyutta Nikāya 56, 11; Majjhima Nikāya 10).', en_expand('There Ven. Sāriputta said, i.e. the Buddha (SN 56.11; MN 10).')
    assert en_expand('he said "Venus" and Seven Sāriputta') == 'he said "Venus" and Seven Sāriputta'  # not inside words
    assert ru_soften('боль', ['b', 'ˈ', 'o', 'ɭ']) == ['b', 'ˈ', 'o', 'ɭ', 'ʲ']
    assert ru_soften('мать', ['m', 'ˈ', 'ɑ', 't', 'ʲ']) == ['m', 'ˈ', 'ɑ', 't', 'ʲ']  # т: espeak got it right

    class _V:  # stand-in for a Piper voice: two sentences, as espeak splits them
        @staticmethod
        def phonemize(t):
            return [list('bˈoɭ?'), list('ˈɛtʌ bˈoɭ.')]
    assert [''.join(x) for x in ru_phonemes(_V, 'Боль? Это боль.')] == ['bˈoɭʲ?', 'ˈɛtʌ bˈoɭʲ.']
    print('ok')
