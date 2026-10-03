// Reference "as DG reads it now": the exact voice.js Pali pipeline + Google pa-IN Chirp3 voice.
// Usage: node baseline_google.js  -> out/<id>.google.mp3, out/devanagari.json
const fs = require('fs');
const VOICE_JS = '/var/www/dg-node-test/public/overrides/read/js/voice.js';
const KEY = JSON.parse(fs.readFileSync('/var/www/dg-node-test/configs/local/tts-config.json', 'utf8')).key;
const src = fs.readFileSync(VOICE_JS, 'utf8');

// Pull the three pieces of voice.js that shape Pali text before it reaches Google.
const window = {};
eval(src.match(/window\.convertPaliToDevanagari = function[\s\S]*?\n};/)[0]);
eval(src.match(/function cleanTextForTTS\(text\)[\s\S]*?\n}/)[0]);
const patch = src.match(/\/\/ === GOOGLE-SPECIFIC PALI PATCH[\s\S]*?\n      if \(text\) \{([\s\S]*?)\n      \}\n/)[1];
const googlePatch = new Function('text', patch + '\nreturn text;');
// Same patch with the bare न/म lengthening limited to word end (the live regex lengthens every
// bare na/ma: manomayā -> mānomāyā). Fails loudly if voice.js changes shape.
const fixedSrc = patch.replace("/न(?![ािीुूेोृॄॢॣंःँ्])/g", "/न(?![ािीुूेोृॄॢॣंःँ्])(?=\\s|[।,:;.?!\"]|$)/g")
                      .replace("/म(?![ािीुूेोृॄॢॣंःँ्])/g", "/म(?![ािीुूेोृॄॢॣंःँ्])(?=\\s|[।,:;.?!\"]|$)/g");
if (fixedSrc === patch) throw new Error('na/ma patch not found in voice.js');
const googlePatchFixed = new Function('text', fixedSrc + '\nreturn text;');

const cases = fs.readFileSync(__dirname + '/cases.tsv', 'utf8').trim().split('\n').slice(1).map(l => l.split('\t'));
fs.mkdirSync(__dirname + '/out', { recursive: true });

(async () => {
    const dev = {};
    for (const [id, text] of cases) {
        const d = cleanTextForTTS(window.convertPaliToDevanagari(text));
        const g = googlePatch(d);
        dev[id] = { devanagari: d, google: g, fixed: googlePatchFixed(d) };
        const out = `${__dirname}/out/${id}.google.mp3`;
        if (fs.existsSync(out)) continue;
        const r = await fetch('https://texttospeech.googleapis.com/v1/text:synthesize?key=' + KEY, {
            method: 'POST',
            headers: { 'content-type': 'application/json', Referer: 'https://dhamma.gift/' },
            body: JSON.stringify({
                input: { text: g },
                voice: { languageCode: 'pa-IN', name: 'pa-IN-Chirp3-HD-Achird' },
                audioConfig: { audioEncoding: 'MP3', speakingRate: 1 },
            }),
        });
        const j = await r.json();
        if (!j.audioContent) { console.error(id, JSON.stringify(j).slice(0, 300)); continue; }
        fs.writeFileSync(out, Buffer.from(j.audioContent, 'base64'));
        console.log('google', id);
    }
    fs.writeFileSync(__dirname + '/out/devanagari.json', JSON.stringify(dev, null, 1));
})();
