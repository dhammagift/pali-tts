<?php
// Own-voice recording sessions. GET ?k= -> ids already recorded; POST ?k=&id= with a WAV body -> takes/<id>.flac.
// The key (record.key, not in git) keeps strangers from filling the disk through this public page.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
$dir = '/var/www/pali-tts/takes';
if (!hash_equals(trim(file_get_contents('/var/www/pali-tts/record.key')), (string)($_GET['k'] ?? ''))) {
    http_response_code(403); exit('{"error":"bad key"}');
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = (string)($_GET['id'] ?? '');
    if (!preg_match('/^[a-z0-9.:-]{1,40}$/', $id)) { http_response_code(400); exit('{"error":"bad id"}'); }
    $wav = file_get_contents('php://input', false, null, 0, 20 * 1024 * 1024);
    if (strlen($wav) < 1000 || substr($wav, 0, 4) !== 'RIFF' || substr($wav, 8, 4) !== 'WAVE') {
        http_response_code(400); exit('{"error":"not a wav"}');
    }
    if (disk_free_space($dir) < 1500 * 1024 * 1024) { http_response_code(507); exit('{"error":"disk almost full"}'); }
    $tmp = tempnam(sys_get_temp_dir(), 'take');
    file_put_contents($tmp, $wav);
    $out = "$dir/" . str_replace(':', '_', $id) . '.flac';
    exec('ffmpeg -loglevel error -y -f wav -i ' . escapeshellarg($tmp) . ' -c:a flac ' . escapeshellarg($out) . ' 2>&1', $log, $rc);
    unlink($tmp);
    if ($rc) { http_response_code(500); exit(json_encode(['error' => 'ffmpeg failed', 'log' => $log])); }
    exit('{"ok":true}');
}

$ids = [];
foreach (glob("$dir/*.flac") as $f) $ids[] = str_replace('_', ':', basename($f, '.flac'));
echo json_encode($ids);
