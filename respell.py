"""Pali words inside a translation, respelled so an English or Russian Piper voice says them sanely.

The en/ru voices phonemize with espeak, which reads IAST as English/Russian letters (Vārāṇasī,
Tathāgata -> "th" as in "think", phassa -> "f"). Russian: Pali in Latin -> Cyrillic by Pali sound.
English: diacritics off, aspirates folded into plain stops (an English voice can't aspirate on cue).
"""
import os
import re
import unicodedata

from pali_ipa import to_ipa

PALI_CHARS = 'āīūṭḍṅñṇḷṃṁ'
# Pali without diacritics in an English sentence: doubled aspirates, ññ, or an aspirate opening the word
# (bhikkhu, dhamma, khandha). Not "ddh"/"tth": Buddha and Matthew read fine as English. An opening ph only in Pali's
# own ph- words (phassa, phala, phusati, phuṭṭha): phenomena, philosophy, phase are English (owner 2026-10-17: «пеномна»)
EN_PALI_HINT = re.compile(r'kkh|ggh|cch|jjh|ṭṭh|bbh|ññ|^(?:bh|dh|kh|gh|jh)(?=[aeiou])|^ph(?:ass|us|ut|alas?$)')
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
                    'kassapa jataka devadatta rahula vassa dana khandha nama rupa vedana sanna sankhara vinnana buddha'.split())
# Pali names stressed on the penult, as the owner hears them (make_stress_names.py): ru forms with U+0301 on the
# stressed vowel (espeak ru reads it), en forms that go through our phonemes with that stress
_NAMES = [line.split() for line in open(os.path.join(os.path.dirname(__file__), 'stress_names.tsv'), encoding='utf-8')]
RU_ACCENT = {w.replace('́', ''): w for lang, w in _NAMES if lang == 'ru'}
EN_PENULT = {w for lang, w in _NAMES if lang == 'en'}
# common words espeak stresses wrongly, the same way (owner, 2026-10-16: «видЕнию вместо вИдению» - vision, not apparition);
# per word, so they also hold inside a compound (знание-видение)
RU_ACCENT.update({w.replace('́', ''): w for w in ('ви́дение', 'ви́дения', 'ви́дению', 'ви́дением', 'ви́дении',
                                                 # from мирско́й (lokuttara), espeak says сверхми́рское (owner, stm3-stm5)
                                                 'сверхмирско́й', 'сверхмирско́е', 'сверхмирска́я', 'сверхмирску́ю',
                                                 'сверхмирски́е', 'сверхмирско́му', 'сверхмирски́х',
                                                 'сверхмирски́м', 'сверхмирски́ми', 'сверхмирско́м')})
RU_NAME = re.compile(r'[А-Яа-яЁё]+')
NUCLEUS = re.compile(r'[əaɪiʊueoʌ]ː?')  # a vowel of our Pali IPA
# our Pali IPA (espeak-hi symbols) -> what the English voices were trained on: plain stops (an English voice
# can't aspirate on cue), no retroflex, single consonants
EN_IPA = [('kʰ', 'k'), ('ɡʰ', 'ɡ'), ('cʰ', 'tʃ'), ('ɟʰ', 'dʒ'), ('ʈʰ', 't'), ('ɖʰ', 'd'), ('tʰ', 't'),
          ('dʰ', 'd'), ('pʰ', 'p'), ('bʰ', 'b'), ('ɭʰ', 'l'), ('c', 'tʃ'), ('ɟ', 'dʒ'), ('ʈ', 't'), ('ɖ', 'd'),
          ('ɳ', 'n'), ('ɲ', 'nj'), ('ɭ', 'l'), ('ʋ', 'v'), ('ɾ', 'ɹ'), ('aː', 'ɑː'), ('eː', 'eɪ'), ('e', 'ɛ')]
EN_IPA_RX = re.compile('|'.join(re.escape(k) for k, _ in sorted(EN_IPA, key=lambda kv: -len(kv[0]))))


def en_ipa(word, us=False):
    """One Pali word as English-voice phonemes: dhamma -> dˈʌmɐ, sutta -> sˈʊtɐ, Vārāṇasī -> vɑːɹˈɑːnɐsiː."""
    ipa = to_ipa(word, stress=word not in EN_PENULT, final_m=True)
    if word in EN_PENULT:  # a name: the stress on the penult, a stressed short a full (as to_ipa does)
        v = list(NUCLEUS.finditer(ipa))[-2]
        ipa = ipa[:v.start()] + 'ˈ' + ('ʌ' if v.group() == 'ə' else v.group()) + ipa[v.end():]
    ipa = EN_IPA_RX.sub(lambda m: dict(EN_IPA)[m.group()], ipa)
    ipa = re.sub(r'oː|o', 'oʊ' if us else 'əʊ', ipa.replace('ə', 'ə' if us else 'ɐ'))
    return re.sub(r'(tʃ|dʒ|[kɡtdpbmnlsvhjɹ])\1', r'\1', ipa)  # geminates: English has none


def is_pali_en(low):
    # Round 16: our phonemes won for the common plain-spelled words (sutta, Dhamma, bhikkhus); for words
    # with diacritics (Vārāṇasī, Nibbāna) the respelling was as good or better, so those stay respelled.
    stem = low[:-1] if low.endswith('s') and (low[:-1] in EN_PALI_WORDS or low[:-1] in EN_PENULT) else low
    return stem in EN_PALI_WORDS or stem in EN_PENULT


def en_parts(text, us=False):
    """English text -> [('text', run) | ('ipa', phonemes)]: Pali words get our phonemes, the rest stays for espeak."""
    out, last = [], 0
    for m in WORD.finditer(unicodedata.normalize('NFC', text)):
        low = m.group().lower()
        if not is_pali_en(low):
            continue
        plural = low.endswith('s') and (low[:-1] in EN_PALI_WORDS or low[:-1] in EN_PENULT)
        poss = re.match(r"['’]s\b", text[m.end():])  # Ānanda's: -z, not "es" read apart
        if m.start() > last:
            out.append(('text', text[last:m.start()]))
        out.append(('ipa', en_ipa(low[:-1] if plural else low, us) + ('z' if plural or poss else '')))
        last = m.end() + (2 if poss else 0)
    if last < len(text):
        out.append(('text', text[last:]))
    return out


# Abbreviations of English translations, spelled out: espeak read "Ven." as "ven" plus a sentence-end
# pause, "i.e." as "eye-ee", "SN 56.11" as "es en fifty six point one one" (owner: Ven. Sariputta ->
# Venerable Sariputta and so on).
EN_ABBR = [(re.compile(r'\bVens\.?(?=\s+[A-ZĀĪŪÑ])'), 'Venerables'), (re.compile(r'\bVen\.?(?=\s+[A-ZĀĪŪÑ])'), 'Venerable'),
           (re.compile(r'\bi\.\s?e\.,?'), 'that is,'), (re.compile(r'\be\.\s?g\.,?'), 'for example,'),
           (re.compile(r'\bI\.\s?e\.,?'), 'That is,'), (re.compile(r'\bE\.\s?g\.,?'), 'For example,'),
           (re.compile(r'\betc\.(?=\s*[,;:)])'), 'et cetera'), (re.compile(r'\betc\.'), 'et cetera.'),
           (re.compile(r'\bcf\.'), 'compare'), (re.compile(r'\blit\.'), 'literally'), (re.compile(r'\bSkt\.'), 'Sanskrit'),
           # live is a verb in the suttas (lɪv): espeak says laɪv after "and" (Miles, DG sheet 2026-10-17)
           (re.compile(r'\blive\b'), 'liv'), (re.compile(r'\bLive\b'), 'Liv')]
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
RU_WORD = re.compile('[а-яё\u0301]+(?:-[а-яё\u0301]+)*')


# espeak's stress is wrong for some names (owner, ruvoice1/2: Варанаси, Исипатане): whole words in espeak's style
RU_STRESS = {'варанаси': 'vʌrʌnˈɑsʲɪ', 'исипатана': 'ɪsʲɪpʌtˈɑna', 'исипатане': 'ɪsʲɪpʌtˈɑnʲi',
             'исипатану': 'ɪsʲɪpʌtˈɑnu', 'исипатаной': 'ɪsʲɪpʌtˈɑnəj',
             # корпус текстов: espeak reads the plural корпуса́ (buildings); our texts mean ко́рпуса
             'корпуса': 'kˈorpusʌ',
             # роды (childbirth): espeak reads рода́ми (clans); owner, stm2: «с болезненными родами»
             'родами': 'rˈodʌmʲɪ',
             # a mark on -ого makes espeak read г (сверхмирско́го = …skˈoɡʌ): phonemes instead
             'сверхмирского': 'svʲirxmʲirskˈovʌ'}


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
    # espeak writes рь as r ɪ ^ (a stray vowel and the voices' start-of-text id: четырьмя = четырьиmя, owner stm3): rʲ
    for i in range(len(out) - 3, -1, -1):
        if out[i:i + 4] == ['r', 'ʲ', 'ɪ', '^']:
            del out[i + 2:i + 4]
    return out


def ru_phonemes(voice, text):
    """Phoneme lists (one per sentence) for a Piper Russian voice, with the soft sign restored."""
    text = RU_NAME.sub(lambda m: _case(m.group(), RU_ACCENT[m.group().lower()]) if m.group().lower() in RU_ACCENT else m.group(),
                       respell(text, 'ru'))
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
            if words[wi] in RU_STRESS:  # keep the punctuation glued to the word
                fixed[ti] = list(RU_STRESS[words[wi]]) + [c for c in t if not c.isalpha() and c not in 'ˈˌːʲ']
            elif 'ь' in words[wi]:
                fixed[ti] = ru_soften(words[wi], t)
            f = fixed.get(ti, t)
            k = next((j for j, c in enumerate(f) if c.isalpha() or c == 'ˈ'), len(f))
            if f[k:k + 2] == ['ˈ', 'ɑ']:  # a stressed opening а as ɑ is drawn out, robot-like (owner: алчность); a is not
                fixed[ti] = f[:k + 1] + ['a'] + f[k + 2:]
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


RU_VOWELS, IPA_VOWELS = 'аеёиоуыэюя', 'aɑʌəoɔuʊiɪyɨeɛæɐ'


def ru_stress_marks(voice, text):
    """text with U+0301 on every word's stressed vowel, as our phonemes stress it (espeak + RU_STRESS), for a voice that
    reads letters (Supertonic). A word whose vowel letters and phoneme vowels don't pair one to one stays as it is."""
    def mark(m):
        w = m.group()
        letters = [i for i, c in enumerate(w.lower()) if c in RU_VOWELS]
        # -ого/-его, сегодня: M1 reads его́ with a г (owner, stm4) and stresses them right unmarked
        if len(letters) < 2 or 'ё' in w.lower() or '\u0301' in w or re.search('[ое]го$|сегодн', w.lower()):
            return w
        ph = ''.join(p for s in ru_phonemes(voice, w) for p in s)
        ph = re.sub(f"ˈ([^{IPA_VOWELS}]*)", r"\1ˈ", ph)  # ˈja -> jˈa: the mark right before its vowel
        groups = re.findall(f"ˈ?[{IPA_VOWELS}]", ph)  # one vowel each: наблюдении's ии are two
        stressed = [k for k, g in enumerate(groups) if g.startswith('ˈ')]
        if len(stressed) != 1:
            return w
        k = stressed[0]
        if len(groups) != len(letters):  # espeak adds a vowel (четырьмя: tʃʲityrɪ^mʲˈɑ): only a first or last stress is sure
            k = 0 if k == 0 else -1 if k == len(groups) - 1 else None
            if k is None:
                return w
        i = letters[k] + 1
        if w[i:i + 1].lower() == 'й':  # одно́й: M1 misreads a marked vowel before й (owner, stm4)
            return w
        return w[:i] + '\u0301' + w[i:]
    return re.sub('[А-Яа-яЁё]+', mark, text)

def export():
    """The tables as JSON-able data for web/pali-tts.js (DG reads en/ru translations offline with the same respelling:
    the service hands this out, so the tables live here only). check_js.py runs translations through both."""
    for rx, full in EN_ABBR:
        assert '\\' not in full and '$' not in full, full
    return {'word': WORD.pattern, 'pali_chars': PALI_CHARS, 'en_pali_hint': EN_PALI_HINT.pattern,
            'ru_rx': RU_RX.pattern, 'ru_map': RU_MAP, 'en_rx': EN_RX.pattern, 'en_map': EN_MAP,
            'en_pali_words': sorted(EN_PALI_WORDS), 'en_ipa_rx': EN_IPA_RX.pattern, 'en_ipa': dict(EN_IPA),
            'en_abbr': [[rx.pattern, full] for rx, full in EN_ABBR], 'en_books': EN_BOOKS, 'en_ref': EN_REF.pattern,
            'ru_soften': {k: list(v) for k, v in RU_SOFTEN.items()}, 'ru_word': RU_WORD.pattern, 'ru_stress': RU_STRESS,
            'ru_accent': RU_ACCENT, 'en_penult': sorted(EN_PENULT), 'nucleus': NUCLEUS.pattern}


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
    assert en_expand('E.g. form, feeling, etc., and so on etc. Then') == 'For example, form, feeling, et cetera, and so on et cetera. Then'
    assert en_expand('and live having achieved it. Live!') == 'and liv having achieved it. Liv!'
    assert respell('phenomena, philosophy, phase; phala', 'en') == 'phenomena, philosophy, phase; pala'
    assert RU_STRESS['исипатане'].count('ˈ') == 1
    assert all(v.count('ˈ') == 1 for v in RU_STRESS.values())
    assert en_ipa('dhamma') == 'dˈʌmɐ', en_ipa('dhamma')
    assert en_ipa('sutta') == 'sˈʊtɐ', en_ipa('sutta')
    assert en_ipa('gotamo') == 'ɡˈəʊtɐməʊ', en_ipa('gotamo')
    assert en_parts('the suttas, monks') == [('text', 'the '), ('ipa', 'sˈʊtɐz'), ('text', ', monks')], en_parts('the suttas, monks')
    assert en_parts("Sāriputta's bowl")[:2] == [('ipa', 'sɑːɹɪpˈʊtɐz'), ('text', ' bowl')], en_parts("Sāriputta's bowl")
    assert [k for k, _ in en_parts('in Vārāṇasī the Dhamma')] == ['text', 'ipa']  # diacritics: respelled
    assert en_expand('There Ven. Sāriputta said, i.e. the Buddha (SN 56.11; MN 10).') == \
        'There Venerable Sāriputta said, that is, the Buddha (Saṁyutta Nikāya 56, 11; Majjhima Nikāya 10).', en_expand('There Ven. Sāriputta said, i.e. the Buddha (SN 56.11; MN 10).')
    assert en_expand('he said "Venus" and Seven Sāriputta') == 'he said "Venus" and Seven Sāriputta'  # not inside words
    assert RU_ACCENT['видению'] == 'ви\u0301дению'
    assert RU_ACCENT['раджагахе'] == 'раджага\u0301хе' and en_ipa('sāriputta') == 'sɑːɹɪpˈʊtɐ', en_ipa('sāriputta')
    assert ru_soften('боль', ['b', 'ˈ', 'o', 'ɭ']) == ['b', 'ˈ', 'o', 'ɭ', 'ʲ']
    assert ru_soften('четырьмя', list('tʃʲityrɪ^mʲˈɑ')) == list('tʃʲityrʲmʲˈɑ')
    class _A:
        phonemize = staticmethod(lambda t: [list('ˈɑɭtʃʲnʌstʲ ɪ mʌnˈɑx.')])
    assert ''.join(ru_phonemes(_A, 'Алчность и монах.')[0]) == 'ˈaɭtʃʲnʌstʲ ɪ mʌnˈɑx.'
    assert ru_soften('мать', ['m', 'ˈ', 'ɑ', 't', 'ʲ']) == ['m', 'ˈ', 'ɑ', 't', 'ʲ']  # т: espeak got it right

    class _V:  # stand-in for a Piper voice: two sentences, as espeak splits them
        @staticmethod
        def phonemize(t):
            return [list('bˈoɭ?'), list('ˈɛtʌ bˈoɭ.')]
    assert [''.join(x) for x in ru_phonemes(_V, 'Боль? Это боль.')] == ['bˈoɭʲ?', 'ˈɛtʌ bˈoɭʲ.']

    class _W:  # espeak's phonemes for single words
        phonemize = staticmethod(lambda t: [list({'каково': 'kʌkʌvˈo', 'таковым': 'tʌkʌvˈym', 'это': 'ˈɛtʌ',
                                                  'учитель': 'utʃʲˈitʲɪl', 'родами': 'rʌdˈɑmʲɪ',
                                                  'четырьмя': 'tʃʲityrɪ^mʲˈɑ'}[t.lower()])])
    assert ru_stress_marks(_W, 'Каково это, таковым учитель') == 'Каково\u0301 э\u0301то, таковы\u0301м учи\u0301тель'
    assert ru_stress_marks(_W, 'родами')[:4] == 'ро\u0301д'  # from RU_STRESS
    assert ru_stress_marks(_W, 'четырьмя') == 'четырьмя\u0301'
    assert ru_stress_marks(_W, 'его чего того') == 'его чего того'  # M1 would read the г
    assert ru_stress_marks(_W, 'всё и я') == 'всё и я'  # ё and one-vowel words: nothing to mark
    print('ok')
