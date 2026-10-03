// Synthesize a list of Pali segments with the live voice.js Google pipeline (pa-IN Achird).
// Usage: node google_segments.js segments.json outdir   (segments.json: [[key, iast], ...])
const fs = require('fs');
const VOICE_JS = '/var/www/dg-node-test/public/overrides/read/js/voice.js';
const KEY = JSON.parse(fs.readFileSync('/var/www/dg-node-test/configs/local/tts-config.json', 'utf8')).key;
const src = fs.readFileSync(VOICE_JS, 'utf8');
const window = {};
eval(src.match(/window\.convertPaliToDevanagari = function[\s\S]*?\n};/)[0]);
eval(src.match(/function cleanTextForTTS\(text\)[\s\S]*?\n}/)[0]);
const patch = new Function('text', src.match(/\/\/ === GOOGLE-SPECIFIC PALI PATCH[\s\S]*?\n      if \(text\) \{([\s\S]*?)\n      \}\n/)[1] + '\nreturn text;');
const [segFile, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const segs = JSON.parse(fs.readFileSync(segFile, 'utf8'));
// The exact text Google gets, so other voices can be fed the same patched Devanagari.
fs.writeFileSync(`${out}/texts.json`, JSON.stringify(segs.map(([, iast]) => patch(cleanTextForTTS(window.convertPaliToDevanagari(iast))))));
(async () => {
    for (const [i, [key, iast]] of segs.entries()) {
        const f = `${out}/${String(i).padStart(3, '0')}.mp3`;
        if (fs.existsSync(f)) continue;
        const text = patch(cleanTextForTTS(window.convertPaliToDevanagari(iast)));
        const r = await fetch('https://texttospeech.googleapis.com/v1/text:synthesize?key=' + KEY, {
            method: 'POST', headers: { 'content-type': 'application/json', Referer: 'https://dhamma.gift/' },
            body: JSON.stringify({ input: { text }, voice: { languageCode: 'pa-IN', name: 'pa-IN-Chirp3-HD-Achird' },
                                   audioConfig: { audioEncoding: 'MP3', sampleRateHertz: 24000 } }) });
        const j = await r.json();
        if (!j.audioContent) throw new Error(key + ' ' + JSON.stringify(j).slice(0, 200));
        fs.writeFileSync(f, Buffer.from(j.audioContent, 'base64'));
    }
})();
