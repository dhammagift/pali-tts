// Pali TTS in the browser (DG offline): the same reading as tts_server.py, on the user's device.
// The rules are not copied here: makePali() takes pali_ipa.export() as data (GET /api/tts/pali-ipa.json), and this file
// is only the engine around them. check_js.py runs the corpus through Python and this file; they must agree.
// Usage: const p = makePali(data); const s = await makeSpeaker(ort, p, modelBytes, modelJson); const {pcm, sr} = await s.speak(text, rate)
// Translation voices (en/ru): const t = makeTranslation(respellData, p, await loadEspeak(makeEspeakModule, files)), then
// makeSpeaker(ort, p, modelBytes, modelJson, { translation: t, lang: 'en' | 'ru' }).

export function makePali(d) {
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const TOKEN = new RegExp(d.token, 'g'), WORDS = new RegExp(d.words, 'g'), PEYYALA = new RegExp(d.peyyala, 'g');
  const MONO = new RegExp(d.mono_hiatus, 'g');
  const RULES = d.rules.map(([p, r]) => [new RegExp(p, 'g'), r]);
  const PUNCT_OUT = new Set(Object.values(d.punct));

  const normalize = text => text.toLowerCase().normalize('NFC').replaceAll('ṁ', 'ṃ').replaceAll('ŋ', 'ṃ')
    .replace(PEYYALA, ', peyyāla, ').replaceAll('…', ', ');

  function wordIpa(word, stress, fullA, finalM, lang, heavyBack) {
    const prof = d.profiles[lang], full = has(prof, 'A') ? prof.A : 'ʌ';
    const toks = word.match(TOKEN) || [];
    const out = toks.map((t, i) => {
      if (has(d.vowels, t)) return ['V', t, fullA && t === 'a' ? full : has(prof, t) ? prof[t] : d.vowels[t]];
      if (t === 'ṃ') {
        const nxt = i + 1 < toks.length ? toks[i + 1][0] : '';
        return ['N', t, finalM && !nxt ? 'm' : has(d.nasal_before, nxt) ? d.nasal_before[nxt] : 'ŋ'];
      }
      return ['C', t, has(prof, t) ? prof[t] : d.cons[t]];
    });
    const cn = i => i < out.length && 'CN'.includes(out[i][0]);
    out.forEach((x, i) => { if (x[0] === 'V' && 'eo'.includes(x[1]) && cn(i + 1) && cn(i + 2)) x[2] = x[1]; });
    if (stress) {
      const vidx = out.flatMap((x, i) => x[0] === 'V' ? [i] : []);
      const heavy = vi => {
        let j = vi + 1;
        while (cn(j)) j++;
        return d.long.includes(out[vi][1]) || j - vi - 1 >= 2 || (vi + 1 < out.length && out[vi + 1][0] === 'N');
      };
      let s = null;
      if (vidx.length >= 3) {
        s = heavy(vidx.at(-2)) ? vidx.at(-2) : vidx.at(-3);
        if (heavyBack && vidx.length >= 4 && !heavy(vidx.at(-2)) && !heavy(s) && heavy(vidx.at(-4))) s = vidx.at(-4);
      } else if (vidx.length) s = vidx[0];
      if (s !== null) {
        if (out[s][1] === 'a') out[s][2] = full;
        out[s][2] = 'ˈ' + out[s][2];
      }
    }
    return out.map(x => x[2]).join('');
  }

  function toIpa(text, { stress = true, fullA = false, finalM = false, lang = 'hi', heavyBack = true } = {}) {
    const parts = [];
    for (const [tok] of normalize(text).matchAll(WORDS)) {
      if (has(d.punct, tok)) {
        if (parts.length && PUNCT_OUT.has(parts.at(-1))) continue;
        parts.push(d.punct[tok]);
      } else parts.push(wordIpa(tok, stress, fullA, finalM, lang, heavyBack));
    }
    return parts.join(' ').replace(/ ([,.?!])/g, '$1').replace(/^[ ,]+|[ ,]+$/g, '');
  }

  function tune(ipa) {
    for (const [rx, rep] of RULES) ipa = ipa.replace(rx, rep);
    return ipa.replace(MONO, (m, g1) => g1 === 'sˈoː' ? 'soːoːoː ' : g1 + ', ');
  }

  return { normalize, toIpa, tune };
}

// Piper's espeak phonemizer (piper-tts 1.8.0 phonemize_espeak.py) on web/espeak (the same espeak-ng commit, built
// to WebAssembly). files: {path in espeak-ng-data: bytes}. makeModule: web/espeak/espeak.mjs's default export.
export async function loadEspeak(makeModule, files, moduleOpts = {}) {
  const m = await makeModule(moduleOpts);
  for (const [path, bytes] of Object.entries(files)) {
    m.FS.mkdirTree('/d/' + path.split('/').slice(0, -1).join('/'));
    m.FS.writeFile('/d/' + path, bytes);
  }
  if (m.ccall('dg_init', 'number', ['string'], ['/d']) < 0) throw new Error('espeak-ng did not start');
  function phonemize(voice, text) {  // -> sentences, each a list of phonemes (code points), as voice.phonemize
    if (m.ccall('dg_voice', 'number', ['string'], [voice]) !== 0) throw new Error('espeak-ng has no voice ' + voice);
    const t = m.stringToNewUTF8(text), r = m._dg_phonemes(t), out = m.UTF8ToString(r);
    m._free(t);
    m._free(r);
    const all = [];
    let sent = [];
    for (const line of out.slice(0, -1).split('\n')) {
      const [ph, term, end] = line.split('\t');
      // (lang) switch flags around words of another language go; punctuation stays, a clause gets a space after it
      sent.push(...(ph.replace(/\([^)]+\)/g, '') + term + ([',', ':', ';'].includes(term) ? ' ' : '')).normalize('NFD'));
      if (end === '1') {
        all.push(sent);
        sent = [];
      }
    }
    if (sent.length) all.push(sent);
    if (all.length && !all.at(-1).length) all.pop();
    return all;
  }
  return { phonemize };
}

// respell.py for the en/ru voices (Pali words inside a translation, abbreviations, the soft sign): its tables come as data
// (respell.export()), this is only the code around them. check_js.py runs translations through both.
export function makeTranslation(d, pali, espeak) {
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const WORD = new RegExp(d.word, 'g'), HINT = new RegExp(d.en_pali_hint), RU_RX = new RegExp(d.ru_rx, 'g');
  const EN_RX = new RegExp(d.en_rx, 'g'), EN_IPA_RX = new RegExp(d.en_ipa_rx, 'g'), REF = new RegExp(d.en_ref, 'g');
  const ABBR = d.en_abbr.map(([p, full]) => [new RegExp(p, 'g'), full]), RU_WORD = new RegExp(d.ru_word, 'g');
  const PALI_WORDS = new Set(d.en_pali_words);
  const alpha = c => /\p{L}/u.test(c);  // Python's str.isalpha
  const cased = (src, out) => {
    const c = src.slice(0, 1);
    return c && c === c.toUpperCase() && c !== c.toLowerCase() ? out.slice(0, 1).toUpperCase() + out.slice(1) : out;
  };

  function respell(text, lang) {
    text = text.normalize('NFC');
    if (lang !== 'ru' && lang !== 'en') return text;
    return text.replace(WORD, w => {
      const low = w.toLowerCase();
      if (lang === 'ru') return cased(w, low.replace(RU_RX, x => d.ru_map[x]));
      if ([...low].some(c => d.pali_chars.includes(c)) || HINT.test(low)) return cased(w, low.replace(EN_RX, x => d.en_map[x]));
      return w;
    });
  }

  const isPaliEn = low => PALI_WORDS.has(low.endsWith('s') && PALI_WORDS.has(low.slice(0, -1)) ? low.slice(0, -1) : low);

  function enIpa(word, us) {
    let ipa = pali.toIpa(word, { finalM: true }).replace(EN_IPA_RX, m => d.en_ipa[m]);
    ipa = ipa.replaceAll('ə', us ? 'ə' : 'ɐ').replace(/oː|o/g, us ? 'oʊ' : 'əʊ');
    return ipa.replace(/(tʃ|dʒ|[kɡtdpbmnlsvhjɹ])\1/g, '$1');
  }

  function enParts(text, us) {
    const out = [];
    let last = 0;
    for (const m of text.normalize('NFC').matchAll(WORD)) {
      const low = m[0].toLowerCase();
      if (!isPaliEn(low)) continue;
      const plural = low.endsWith('s') && PALI_WORDS.has(low.slice(0, -1));
      if (m.index > last) out.push(['text', text.slice(last, m.index)]);
      out.push(['ipa', enIpa(plural ? low.slice(0, -1) : low, us) + (plural ? 'z' : '')]);
      last = m.index + m[0].length;
    }
    if (last < text.length) out.push(['text', text.slice(last)]);
    return out;
  }

  function enExpand(text) {
    for (const [rx, full] of ABBR) text = text.replace(rx, full);
    return text.replace(REF, (m, book, a, b) => `${d.en_books[book]} ${a}` + (b ? `, ${b}` : ''));
  }

  function enPhonemes(voice, idMap, text) {
    text = enExpand(text);
    const us = voice === 'en-us';
    let seq = [];
    for (const [kind, val] of enParts(text, us)) {
      let ph = kind === 'text' ? espeak.phonemize(voice, respell(val, 'en')).flat() : [...val];
      const lead = kind === 'text' ? val.match(/^\s*([,.;:?!])/) : null;
      if (lead && (!ph.length || ph[0] !== lead[1])) ph = [lead[1], ' ', ...ph];  // espeak drops a leading pause
      if (ph.length) seq.push(...(seq.length && !',.?!;:'.includes(ph[0]) ? [' '] : []), ...ph);
    }
    seq = seq.filter((p, i) => !(p === ' ' && i && seq[i - 1] === ' '));
    return seq.filter(p => has(idMap, p));
  }

  function ruSoften(word, phonemes) {
    const out = [...phonemes];
    for (const [letter, bases] of Object.entries(d.ru_soften)) {
      if (!word.includes(letter + 'ь')) continue;
      const idx = out.flatMap((p, i) => bases.includes(p) ? [i] : []);
      const letters = [...word.matchAll(new RegExp(letter, 'g'))].map(m => m.index);
      if (idx.length !== letters.length) continue;
      for (let k = letters.length - 1; k >= 0; k--) {
        const pos = letters[k], i = idx[k];
        if (word.slice(pos + 1, pos + 2) === 'ь' && (i + 1 >= out.length || out[i + 1] !== 'ʲ')) out.splice(i + 1, 0, 'ʲ');
      }
    }
    return out;
  }

  function ruPhonemes(voice, text) {
    text = respell(text, 'ru');
    const words = text.toLowerCase().match(RU_WORD) || [];
    const sents = espeak.phonemize(voice, text).filter(s => s.length);
    const tokens = [];
    let cur = [];
    for (const p of sents.flatMap(s => [...s, ' '])) {
      if (p !== ' ') cur.push(p);
      else {
        if (cur.length) tokens.push(cur);
        cur = [];
      }
    }
    if (tokens.filter(t => t.some(alpha)).length !== words.length) return sents;
    const fixed = new Map();
    let wi = 0;
    tokens.forEach((t, ti) => {
      if (!t.some(alpha)) return;
      const w = words[wi++];
      if (has(d.ru_stress, w)) fixed.set(ti, [...d.ru_stress[w], ...t.filter(c => !alpha(c) && !'ˈˌːʲ'.includes(c))]);
      else if (w.includes('ь')) fixed.set(ti, ruSoften(w, t));
    });
    let ti = 0;
    return sents.map(s => {
      const out = [];
      let word = [];
      for (const p of [...s, ' ']) {
        if (p !== ' ') word.push(p);
        else {
          if (word.length) out.push(...(fixed.get(ti++) ?? word));
          word = [];
          out.push(' ');
        }
      }
      return out.slice(0, -1);
    });
  }

  // tts_server.synth_pcm's phoneme lists for one sentence of a translation
  const phonemes = (lang, voice, idMap, sent) => lang === 'en' ? [enPhonemes(voice, idMap, sent)].filter(p => p.length)
    : ruPhonemes(voice, sent).filter(p => p.length);
  return { respell, enParts, enExpand, phonemes };
}

// tts_server.synth_pcm for a 'pi' voice: sentence by sentence, 0.35 s between; a lone word read inside "W, W." and the
// second W cut out by the model's own durations (needs the align model: its second output is per-id frames).
const SENTENCE = /(?<=[.?!;:])\s+/;
const HOP = 256;

export async function makeSpeaker(ort, pali, modelBytes, modelJson, { noise = 0.6, noiseW = 0.7, translation = null, lang = 'pi' } = {}) {
  const session = await ort.InferenceSession.create(modelBytes, { executionProviders: ['wasm'] });
  const idMap = modelJson.phoneme_id_map, sr = modelJson.audio.sample_rate;
  const ids = chars => {
    const out = [...idMap['^'], ...idMap['_']];
    for (const c of chars) if (idMap[c]) out.push(...idMap[c], ...idMap['_']);
    return [...out, ...idMap['$']];
  };
  async function run(chars, length) {
    const x = ids(chars);
    const r = await session.run({
      input: new ort.Tensor('int64', BigInt64Array.from(x, BigInt), [1, x.length]),
      input_lengths: new ort.Tensor('int64', BigInt64Array.from([BigInt(x.length)]), [1]),
      scales: new ort.Tensor('float32', Float32Array.from([noise, length, noiseW]), [3]),
    });
    const [audio, dur] = session.outputNames.map(n => r[n]);
    return { audio: audio.data, dur: dur && dur.data };
  }
  async function loneWord(ipa, length) {
    const { audio, dur } = await run([...`${ipa}, ${ipa}.`], length);
    if (!dur) return (await run([...ipa + '.'], length)).audio;
    let first = 0;
    for (let i = 0; i < 2 + 2 * ([...ipa].length + 2); i++) first += Math.trunc(Number(dur[i])) * HOP;
    return audio.slice(Math.max(first - Math.trunc(0.03 * sr), 0));
  }
  async function speak(text, rate = 1) {
    // pratham: our tuned pace (length 1.15 at rate 1); translations: the recorded pace
    const length = (translation ? 1 : 1.15) / rate, gap = new Float32Array(Math.trunc(sr * 0.35)), parts = [];
    for (const sent of text.trim().split(SENTENCE)) {
      if (translation) {  // en/ru: no lone-word trick (Pali only)
        const lists = translation.phonemes(lang, modelJson.espeak.voice, idMap, sent);
        for (const ph of lists) parts.push((await run(ph, length)).audio);
        if (lists.length) parts.push(gap);
        continue;
      }
      const ipa = pali.tune(pali.toIpa(sent, { fullA: true }));
      const word = ipa.replace(/^[ ,.?!:;]+|[ ,.?!:;]+$/g, '');
      if (word && !word.includes(' ')) parts.push(await loneWord(word, length), gap);
      else if (ipa.replace(/^[ ,.?!]+|[ ,.?!]+$/g, '')) parts.push((await run([...ipa], length)).audio, gap);
    }
    if (!parts.length) parts.push(new Float32Array(sr >> 2));
    const pcm = new Float32Array(parts.reduce((n, p) => n + p.length, 0));
    parts.reduce((o, p) => (pcm.set(p, o), o + p.length), 0);
    return { pcm, sr };
  }
  return { speak };
}

// 16-bit mono WAV, base64: plays like the server's {audioContent} mp3 (voice.js sets the data: URL's type from it)
export function wavBase64(pcm, sr) {
  const buf = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const str = (o, s) => [...s].forEach((c, i) => buf.setUint8(o + i, c.charCodeAt(0)));
  str(0, 'RIFF'); buf.setUint32(4, 36 + pcm.length * 2, true); str(8, 'WAVEfmt ');
  buf.setUint32(16, 16, true); buf.setUint16(20, 1, true); buf.setUint16(22, 1, true);
  buf.setUint32(24, sr, true); buf.setUint32(28, sr * 2, true); buf.setUint16(32, 2, true); buf.setUint16(34, 16, true);
  str(36, 'data'); buf.setUint32(40, pcm.length * 2, true);
  pcm.forEach((v, i) => buf.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 32767, true));
  const bytes = new Uint8Array(buf.buffer);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}
