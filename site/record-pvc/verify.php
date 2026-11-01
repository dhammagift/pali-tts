<?php
// ElevenLabs PVC voice verification for the owner's Russian clone (2026-11-01).
// The captcha must be answered within a short time after it is fetched, so the page shows it and
// records right away. GET ?k=&captcha=1 -> the phrase (PNG); POST ?k= with a WAV -> verify, then train.
// The ElevenLabs key (el.key) and the voice id (pvc-voice.id) live outside the web root, not in git.
header('Cache-Control: no-store');
if (!hash_equals(trim(file_get_contents('/var/www/pali-tts/record-sn.key')), (string)($_GET['k'] ?? ''))) {
    http_response_code(403); exit('bad key');
}
$key = trim(file_get_contents('/var/www/pali-tts/el.key'));
$voice = trim(file_get_contents('/var/www/pali-tts/pvc-voice.id'));
$base = "https://api.elevenlabs.io/v1/voices/pvc/$voice";

function el($url, $key, $post = null, $json = false) {
    $c = curl_init($url);
    $h = ["xi-api-key: $key"];
    if ($json) $h[] = 'Content-Type: application/json';
    curl_setopt_array($c, [CURLOPT_RETURNTRANSFER => true, CURLOPT_HTTPHEADER => $h, CURLOPT_TIMEOUT => 60]);
    if ($post !== null) curl_setopt_array($c, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $post]);
    $body = curl_exec($c);
    $code = curl_getinfo($c, CURLINFO_HTTP_CODE);
    curl_close($c);
    return [$code, $body];
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    [$code, $body] = el("$base/captcha", $key);
    http_response_code($code);
    header('Content-Type: ' . ($code === 200 ? 'image/png' : 'application/json'));
    exit($body);
}

header('Content-Type: application/json; charset=utf-8');
// The page sends opus (webm/ogg) or aac (mp4) from MediaRecorder, a WAV where there is none.
$types = ['audio/webm' => 'webm', 'audio/ogg' => 'ogg', 'audio/mp4' => 'm4a', 'audio/wav' => 'wav'];
$type = strtolower(trim(explode(';', $_SERVER['CONTENT_TYPE'] ?? '')[0]));
$ext = $types[$type] ?? null;
$audio = file_get_contents('php://input', false, null, 0, 4 * 1024 * 1024);
if (!$ext || strlen($audio) < 1000) { http_response_code(400); exit('{"error":"not audio"}'); }
$tmp = tempnam(sys_get_temp_dir(), 'pvc') . ".$ext";
file_put_contents($tmp, $audio);
copy($tmp, '/var/www/pali-tts/takes-sn/captcha-' . time() . ".$ext");  // keep the try, to see what was sent
[$code, $body] = el("$base/captcha", $key, ['recording' => new CURLFile($tmp, $type, "captcha.$ext")]);
unlink($tmp);
if ($code !== 200) { http_response_code($code); exit(json_encode(['verified' => false, 'el' => json_decode($body, true)])); }
[$tcode, $tbody] = el("$base/train", $key, json_encode(['model_id' => 'eleven_multilingual_v2']), true);
exit(json_encode(['verified' => true, 'train' => $tcode, 'el' => json_decode($tbody, true)]));
