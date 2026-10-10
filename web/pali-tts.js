// Pali TTS in the browser (DG offline): the same reading as tts_server.py, on the user's device.
// The rules are not copied here: makePali() takes pali_ipa.export() as data (GET /api/tts/pali-ipa.json), and this file
// is only the engine around them. check_js.py runs the corpus through Python and this file; they must agree.
// Usage: const p = makePali(data); const s = await makeSpeaker(ort, p, modelBytes, modelJson); const {pcm, sr} = await s.speak(text, rate)

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

// tts_server.synth_pcm for a 'pi' voice: sentence by sentence, 0.35 s between; a lone word read inside "W, W." and the
// second W cut out by the model's own durations (needs the align model: its second output is per-id frames).
const SENTENCE = /(?<=[.?!;:])\s+/;
const HOP = 256;

export async function makeSpeaker(ort, pali, modelBytes, modelJson, { noise = 0.6, noiseW = 0.7 } = {}) {
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
    const length = 1.15 / rate, gap = new Float32Array(Math.trunc(sr * 0.35)), parts = [];
    for (const sent of text.trim().split(SENTENCE)) {
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
