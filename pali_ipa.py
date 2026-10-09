"""Pali (IAST) -> IPA phonemes in the espeak-hi inventory that Piper hi_IN voices were trained on.

Pali spelling is phonemic, so this is a deterministic table: no schwa deletion, every vowel is spoken.
"""
import re
import unicodedata

VOWELS = {'a': 'ə', 'ā': 'aː', 'i': 'ɪ', 'ī': 'iː', 'u': 'ʊ', 'ū': 'uː', 'e': 'eː', 'o': 'oː'}
LONG = {'ā', 'ī', 'ū', 'e', 'o'}
CONS = {
    'kh': 'kʰ', 'gh': 'ɡʰ', 'ch': 'cʰ', 'jh': 'ɟʰ', 'ṭh': 'ʈʰ', 'ḍh': 'ɖʰ',
    'th': 'tʰ', 'dh': 'dʰ', 'ph': 'pʰ', 'bh': 'bʰ', 'ḷh': 'ɭʰ',
    'k': 'k', 'g': 'ɡ', 'c': 'c', 'j': 'ɟ', 'ṭ': 'ʈ', 'ḍ': 'ɖ', 't': 't', 'd': 'd', 'p': 'p', 'b': 'b',
    'ṅ': 'ŋ', 'ñ': 'ɲ', 'ṇ': 'ɳ', 'n': 'n', 'm': 'm',
    'y': 'j', 'r': 'ɾ', 'l': 'l', 'ḷ': 'ɭ', 'v': 'ʋ', 's': 's', 'h': 'h',
}
# Niggahita takes the place of articulation of the following stop.
NASAL_BEFORE = {'k': 'ŋ', 'g': 'ŋ', 'c': 'ɲ', 'j': 'ɲ', 'ṭ': 'ɳ', 'ḍ': 'ɳ', 't': 'n', 'd': 'n', 'p': 'm', 'b': 'm'}
TOKEN = re.compile('|'.join(sorted(CONS, key=len, reverse=True)) + '|ṃ|[aāiīuūeo]')
# Per-voice-language overrides: each Piper voice only knows the symbols its espeak language emits.
# 'A' = full short a.
PROFILES = {
    'hi': {}, 'mr': {}, 'ur': {'r': 'r'},
    'ne': {'u': 'u'},
    'ml': {'A': 'ɐ', 'i': 'i', 'u': 'u'},
    'te': {'A': 'a', 'i': 'i', 'u': 'u', 'r': 'r'},
}
PEYYALA = re.compile(r'(?:…|\.\.\.)\s*p[ae]\s*(?:…|\.\.\.)')
PUNCT = {',': ',', ';': ',', ':': ',', '—': ',', '–': ',', '.': '.', '?': '?', '!': '!'}


def normalize(text):
    text = unicodedata.normalize('NFC', text.lower())
    # "…pe…" / "…pa…" mark a passage left out: read as "peyyāla" (owner: without it only someone who knows
    # the text by heart can tell anything was skipped), set off by short pauses
    text = PEYYALA.sub(', peyyāla, ', text.replace('ṁ', 'ṃ').replace('ŋ', 'ṃ'))
    return text.replace('…', ', ')


def word_ipa(word, stress=True, full_a=False, final_m=False, lang='hi', heavy_back=True):
    prof = PROFILES[lang]
    full = prof.get('A', 'ʌ')
    toks = TOKEN.findall(word)
    out = []  # list of (kind, base_letter, ipa)
    for i, t in enumerate(toks):
        if t in VOWELS:
            out.append(['V', t, full if full_a and t == 'a' else prof.get(t, VOWELS[t])])
        elif t == 'ṃ':
            nxt = toks[i + 1][0] if i + 1 < len(toks) else ''
            out.append(['N', t, 'm' if final_m and not nxt else NASAL_BEFORE.get(nxt, 'ŋ')])
        else:
            out.append(['C', t, prof.get(t, CONS[t])])
    # e/o are short before a consonant cluster (metta, sotthi)
    for i, (k, b, _) in enumerate(out):
        if k == 'V' and b in 'eo' and i + 2 < len(out) and out[i + 1][0] in 'CN' and out[i + 2][0] in 'CN':
            out[i][2] = b
    # geminate aspirates: kkh -> k kʰ (already so), keep as is
    if stress:
        vidx = [i for i, x in enumerate(out) if x[0] == 'V']

        def heavy(vi):
            b = out[vi][1]
            after = 0
            j = vi + 1
            while j < len(out) and out[j][0] in 'CN':
                after += 1
                j += 1
            return b in LONG or after >= 2 or (vi + 1 < len(out) and out[vi + 1][0] == 'N')

        if len(vidx) >= 3:
            s = vidx[-2] if heavy(vidx[-2]) else vidx[-3]
            # heavy_back (round 14): a light antepenult yields to a heavy syllable right before it
            # (pītisukhaṁ -> PĪtisukhaṁ, not pīTIsukhaṁ "пи-ити"; vāRĀṇasī as in Hindi). Only the
            # neighbour: reaching further put it on BRAHmacariyaṁ, which the owner marked wrong.
            if heavy_back and len(vidx) >= 4 and not heavy(vidx[-2]) and not heavy(s) and heavy(vidx[-4]):
                s = vidx[-4]
        elif vidx:
            s = vidx[0]
        else:
            s = None
        if s is not None:
            if out[s][1] == 'a':
                out[s][2] = full
            out[s][2] = 'ˈ' + out[s][2]
    return ''.join(x[2] for x in out)


def to_ipa(text, stress=True, full_a=False, final_m=False, lang='hi', heavy_back=True):
    """full_a: short a as a full vowel everywhere instead of reduced ə (Hindi voices swallow ə).
    final_m: word-final niggahita as m (paṭhamam jhānam) instead of ŋ, which the voices tend to drop."""
    parts = []
    for m in re.finditer(r"[a-zāīūṭḍṅñṇḷṃ]+|[,;:.?!—–]", normalize(text)):
        tok = m.group()
        if tok in PUNCT:
            if parts and parts[-1] in PUNCT.values():
                continue
            parts.append(PUNCT[tok])
        else:
            parts.append(word_ipa(tok, stress, full_a, final_m, lang, heavy_back))
    s = ' '.join(parts)
    return re.sub(r' ([,.?!])', r'\1', s).strip(' ,')


# Piper hi_IN pratham, listening round 4: plain ɲ comes out as "n" (ñāṇa -> "nana"), ɲɲ as "n"
# (abhiññā -> "abhinā"), a word-final ŋ as a literal "n-g" (no sonorant ṁ reachable). These spellings won.
PRATHAM_RULES = [
    (re.compile(r'ɲɲ'), 'ɲːj'),  # round 5: ɲːj beat ɲː and nɲː
    (re.compile(r'(?<![ɲ])ɲ(?![ɲːjcɟ])'), 'ɲj'),
    (re.compile(r'ŋ(?=[ ,.?!]|$)'), 'ŋŋ'),  # round 8: ŋŋ is the velar ṁ (ङ) without the "-g" the voice adds to ŋ
    # (round 9's "open a" for an unstressed medial ʌ, added for viharati -> "viharti", is gone: round 22
    # found it behind most syllables swallowed since - jarāpi "japi", paṭhamaṁ, ponobbhavikā, taṇhāya)
    # round 12 (3 takes each): a single c between vowels still came out as "shch" 2 times of 3;
    # doubled cc was right every time
    (re.compile(r'(?<=[ʌaeoiuɪʊː])c(?=[ʌaeoiuɪʊːˈ])'), 'cc'),
    # round 36: the same for j (kāyasamphassajaṁ): doubled jj was ok in all 4 takes, single j bad in 1
    (re.compile(r'(?<=[ʌaeoiuɪʊː])ɟ(?=[ʌaeoiuɪʊːˈ])'), 'ɟɟ'),
    # round 18: y after a short vowel glided into it and its syllable was lost (passambhayaṁ ->
    # "пасамбхам"); doubled jj had no bad take of 8. Not after a long vowel or ɲː (ññ is ɲːj).
    # Only after a (rounds 25, 27): after i it hurt - dutiyaṁ, appaṭivattiyaṁ read better with one y.
    # Round 35: not before i (vedayitaṁ «ведайеиа»; a single y was ok in both takes)
    (re.compile(r'(?<=[ʌa])j(?=[ʌaeouʊˈ])'), 'jj'),
    # round 21: a word-initial ñ came out as "я" (Ñāṇañca -> "янанча"); n + j was the one that worked
    (re.compile(r'(?<![^ ,])ɲj'), 'nj'),
    # round 25: ñ before c as n (kiñci was right only as "kinci")
    (re.compile(r'ɲ(?=c)'), 'n'),
    # round 25: muhuttena - the h between two short u swallowed them; tense u held
    (re.compile(r'ʊhʊ'), 'uhu'),
    # round 33: samphassa from the aspirated pʰ came out as «сасфасса» (m lost, ph as f); p + h was ok in
    # both takes (round 34: j stays ɟ, dʒ and dʲ were bad everywhere)
    (re.compile(r'mpʰ'), 'mph'),
    # round 24: viharati read "viharti" once the open-a rule was gone; an open a in the verb ending
    # -ati (word-final) brought it back, without the swallowing the general rule caused (round 22)
    (re.compile(r'ʌ(?=tɪ(?=[ ,.?!:;]|$))'), 'a'),
    # pratham has no word-final [ŋ] (Hindi has it only before k/g). Round 29: what Hindi itself does with
    # an anusvara won (6 best of 10) - दुक्खं dʊkkʰən, चक्खुं cʌkkʰũ; the explicit "ng" of rounds 24-26 was
    # heard as a literal «НГ». -iṁ stays "im" (paccaññāsiṁ; imasmiṁ was bad every way)
    (re.compile(r'[ʌa]ŋŋ(?=[ ,.?!:;]|$)'), 'ən'),
    # rounds 31-32: after h that ə came out as "e" (arahaṁ «арахем»); a full a there was ok in every take
    (re.compile(r'(?<=h)ən(?=[ ,.?!:;]|$)'), 'ʌn'),
    (re.compile(r'ʊŋŋ(?=[ ,.?!:;]|$)'), 'u\u0303'),  # u + combining tilde: the voice's map has no precomposed ũ
    (re.compile(r'(?<=ɪ)ŋŋ(?=[ ,.?!:;]|$)'), 'm'),
    # round 38: tiṇṇaṁ was bad as ɳɳən in both engines; a long ɳ won (best + ok), full a / dental nn did not
    (re.compile(r'ɳɳ(?=ən(?=[ ,.?!:;]|$))'), 'ɳː'),
    # rounds 38-39: the final -ha of Tasmātiha was not heard at all (hʌ, ha, ɦʌ, ɦaː); a long a won (best + ok)
    (re.compile(r'(?<=ɪ)hʌ(?=[ ,.?!:;]|$)'), 'haː'),
    # rounds 38-40: an unstressed word-final o inside a phrase was heard short next to a long ā (measured: ~110 ms
    # vs ~140 ms stressed ā). oːː, ˌoː, ˈoː, ɔːː, oːˑ (rounds 38-39) were all still short; a triple oː (~230 ms)
    # won in both phrases (best + ok). Only before the next word: phrase-final o is already long (~300 ms), and a
    # stressed one-syllable word (sˈoː, khˈoː) keeps its own o.
    (re.compile(r'(?<=[^ ,ˈˌ])oː(?= )'), 'oːoːoː'),
    # rounds 20, 41: ṭṭh came out as an affricate (sammādiṭṭhi «дичи», diṭṭhupādānaṁ «диччупадана»); a long ʈː
    # was the best spelling in both rounds (r20: 3 best 5 ok; r41: ok/ok, the only one with no bad take)
    (re.compile(r'ʈʈʰ'), 'ʈːʰ'),
    # round 41: the a after r in saṅkhāra- compounds was swallowed («санкхарпаччая»); a long aː won (best + ok)
    (re.compile(r'(?<=kʰaːɾ)ʌ(?=[^ ,.?!:;ˈʌaeoiuɪʊː])'), 'aː'),
    # round 42: pana before a comma read «пан» (now: ok/bad); an open a, aː and ʌː were all ok/ok - the open a, the
    # smallest change, for the word pana wherever it stands
    (re.compile(r'(?<![^ ,])pˈʌnʌ(?=[ ,.?!:;]|$)'), 'pˈʌna'),
]


# Round 17: a one-syllable word ending in a vowel before a word starting with one ("So evamāha") came out
# as "сори эвамаха" in one take of two; a short pause between them was right in both. A glottal stop lost
# everywhere, and longer words (āyasmā ānando) were fine as they are, so only this case.
MONO_HIATUS = re.compile(r'(?<![^ ,])([^ ,.?!ʌəaeoiuɪʊ]*ˈ?[ʌəaeoiuɪʊ]ː?) (?=ˈ?[ʌəaeoiuɪʊ])')


def tune(ipa, rules=PRATHAM_RULES):
    for rx, rep in rules:
        ipa = rx.sub(rep, ipa)
    return MONO_HIATUS.sub(r'\1, ', ipa)


DEVA_C = {'kh': 'ख', 'gh': 'घ', 'ch': 'छ', 'jh': 'झ', 'ṭh': 'ठ', 'ḍh': 'ढ', 'th': 'थ', 'dh': 'ध', 'ph': 'फ', 'bh': 'भ',
          'ḷh': 'ळ्ह', 'k': 'क', 'g': 'ग', 'ṅ': 'ङ', 'c': 'च', 'j': 'ज', 'ñ': 'ञ', 'ṭ': 'ट', 'ḍ': 'ड', 'ṇ': 'ण',
          't': 'त', 'd': 'द', 'n': 'न', 'p': 'प', 'b': 'ब', 'm': 'म', 'y': 'य', 'r': 'र', 'l': 'ल', 'ḷ': 'ळ',
          'v': 'व', 's': 'स', 'h': 'ह'}
DEVA_V = {'a': 'अ', 'ā': 'आ', 'i': 'इ', 'ī': 'ई', 'u': 'उ', 'ū': 'ऊ', 'e': 'ए', 'o': 'ओ'}
DEVA_M = {'a': '', 'ā': 'ा', 'i': 'ि', 'ī': 'ी', 'u': 'ु', 'ū': 'ू', 'e': 'े', 'o': 'ो'}
SCRIPT_SHIFT = {'deva': 0, 'knda': 0x380, 'telu': 0x300}  # Unicode Indic blocks share one layout


def to_script(text, script='deva', final_m=True):
    """Pali IAST -> Devanagari/Kannada/Telugu for cloud voices. Every inherent a stays written (no virama tricks)."""
    out = []
    for m in re.finditer(r"[a-zāīūṭḍṅñṇḷṃ]+|[^a-zāīūṭḍṅñṇḷṃ]+", normalize(text)):
        tok = m.group()
        if not tok[0].isalpha():
            out.append(re.sub(r'[—–“”‘’"]', ',', tok))
            continue
        toks, w = TOKEN.findall(tok), ''
        for i, t in enumerate(toks):
            nxt = toks[i + 1] if i + 1 < len(toks) else ''
            if t == 'ṃ':
                w += 'म्' if final_m and not nxt else 'ं'
            elif t in DEVA_V:
                w += DEVA_V[t] if i == 0 or toks[i - 1] in DEVA_V else DEVA_M[t]
            else:
                w += DEVA_C[t] + ('' if nxt in DEVA_V else '्')
        out.append(w)
    s = ''.join(out)
    shift = SCRIPT_SHIFT[script]
    return ''.join(chr(ord(c) + shift) if shift and 0x900 <= ord(c) <= 0x963 else c for c in s)


if __name__ == '__main__':
    no = lambda w: to_ipa(w, stress=False)
    assert no('jarā') == 'ɟəɾaː', no('jarā')
    assert no('sañjāti') == 'səɲɟaːtɪ', no('sañjāti')
    assert no('cakkhusamphasso') == 'cəkkʰʊsəmpʰəssoː', no('cakkhusamphasso')
    assert no('dhamma') == 'dʰəmmə'
    assert no('evaṁ me sutaṁ') == 'eːʋəŋ meː sʊtəŋ'
    assert no('saṃgha') == 'səŋɡʰə' and no('saṅgha') == 'səŋɡʰə'
    assert no('mettā') == 'mettaː' and no('sotthi') == 'sottʰɪ'
    assert no('ñāṇa') == 'ɲaːɳə'
    assert to_ipa('bhagavato') == 'bʰəɡˈʌʋətoː', to_ipa('bhagavato')
    assert to_ipa('dhamma') == 'dʰˈʌmmə'
    assert to_ipa('nibbānāya') == 'nɪbbaːnˈaːjə'
    assert to_ipa('Katame dve?') == 'kˈʌtəmeː dʋˈeː?', to_ipa('Katame dve?')
    assert to_ipa('cakkhusamphassapaccayā', full_a=True).count('ʌ') == 6
    assert to_ipa('paṭhamaṁ jhānaṁ', stress=False, final_m=True) == 'pəʈʰəməm ɟʰaːnəm'
    assert to_ipa('dhamma', full_a=True, lang='ml') == 'dʰˈɐmmɐ'
    assert to_script('paṭhamaṁ jhānaṁ') == 'पठमम् झानम्', to_script('paṭhamaṁ jhānaṁ')
    assert to_script('saṅgho sañjāti') == 'सङ्घो सञ्जाति'
    assert to_script('dhamma', 'knda') == 'ಧಮ್ಮ', to_script('dhamma', 'knda')
    assert to_script('āḷāro', 'telu') == 'ఆళారో', to_script('āḷāro', 'telu')
    assert tune(to_ipa('ñāṇa paññā evaṁ', stress=False)) == 'njaːɳə pəɲːjaː eːʋəŋŋ', tune(to_ipa('ñāṇa paññā evaṁ', stress=False))
    assert tune(to_ipa('pañca sañjāti', stress=False)) == 'pəncə səɲɟaːtɪ'
    assert tune(to_ipa('Dhammacakka vacī cakkhu', full_a=True)) == 'dʰʌmmʌccˈʌkkʌ ʋˈʌcciː cˈʌkkʰʊ'  # word-initial c untouched
    assert to_ipa('pītisukhaṁ', full_a=True, heavy_back=True) == 'pˈiːtɪsʊkʰʌŋ', to_ipa('pītisukhaṁ', full_a=True, heavy_back=True)
    assert to_ipa('bhagavato', heavy_back=True) == to_ipa('bhagavato', heavy_back=False)  # nothing heavy to move to
    assert to_ipa('brahmacariyaṁ', full_a=True) == 'bɾʌhmʌcˈʌɾɪjʌŋ'  # heavy syllable two away: stays
    assert tune(to_ipa('passambhayaṁ', full_a=True)) == 'pʌssˈʌmbʰʌjjən', tune(to_ipa('passambhayaṁ', full_a=True))
    assert 'jj' not in tune(to_ipa('kāya paññā', full_a=True))  # after a long vowel / in ññ: untouched
    assert tune(to_ipa('So evamāha', full_a=True)) == 'sˈoː, eːʋʌmˈaːhʌ', tune(to_ipa('So evamāha', full_a=True))
    assert ', ' not in tune(to_ipa('āyasmā ānando', full_a=True))  # longer words: unchanged
    assert tune(to_ipa('jarāpi paṭhamaṁ', full_a=True)) == 'ɟʌɾˈaːpɪ pˈʌʈʰʌmən'  # no open a any more (round 22)
    assert tune(to_ipa('sammādiṭṭhi …pe… sammāsamādhi', full_a=True)) == 'sʌmmaːdˈɪʈːʰɪ, pejjˈaːlʌ, sʌmmaːsʌmˈaːdʰɪ', tune(to_ipa('sammādiṭṭhi …pe… sammāsamādhi', full_a=True))
    assert normalize('a ...pa... b') == 'a , peyyāla,  b'
    assert tune(to_ipa('kiñci muhuttena viharati', full_a=True)) == 'kˈɪncɪ muhuttˈeːnʌ ʋɪhˈʌɾatɪ'  # rounds 24-25
    assert tune(to_ipa('dutiyaṁ imasmiṁ', full_a=True)) == 'dˈʊtɪjən ɪmˈʌsmɪm'  # one y after i; -aṁ ən, -iṁ m
    assert 'ʋˈeːdʌjɪtən' in tune(to_ipa('vedayitaṁ', full_a=True))
    assert 'sʌmphˈʌssʌɟɟən' in tune(to_ipa('kāyasamphassajaṁ', full_a=True))
    assert tune(to_ipa('arahaṁ ahaṁ', full_a=True)) == 'ˈʌɾʌhʌn ˈʌhʌn'  # round 32
    assert tune(to_ipa('Ātāpī sampajāno satimā.', full_a=True)) == 'aːtˈaːpiː sʌmpʌɟɟˈaːnoːoːoː sˈʌtɪmaː.'  # round 40
    assert tune(to_ipa('yogo karaṇīyo.', full_a=True)) == 'jˈoːɡoːoːoː kʌɾʌɳˈiːjoː.'
    assert tune(to_ipa('Diṭṭhupādānaṁ, saṅkhārapaccayā viññāṇaṁ, saṅkhārā.', full_a=True)) == \
        'dɪʈːʰʊpaːdˈaːnən, sʌŋkʰaːɾaːpˈʌccʌjjaː ʋɪɲːjˈaːɳən, sʌŋkʰˈaːɾaː.'  # rounds 20, 41
    assert tune(to_ipa('Kathañca pana, bhikkhave', full_a=True)) == 'kʌtʰˈʌncʌ pˈʌna, bʰˈɪkkʰʌʋeː'  # round 42
    assert tune(to_ipa('Tasmātiha, bhikkhave', full_a=True)) == 'tʌsmˈaːtɪhaː, bʰˈɪkkʰʌʋeː'  # round 39
    assert tune(to_ipa('Tiṇṇaṁ saṅgati', full_a=True)) == 'tˈɪɳːən sˈʌŋɡatɪ'  # round 38
    assert tune(to_ipa('evaṁ me sutaṁ cakkhuṁ', full_a=True)) == 'ˈeːʋən mˈeː sˈʊtən cˈʌkkʰu\u0303'  # round 29
    print('ok')
