<?php
// Own-voice recording sessions. GET ?k= -> ids already recorded; GET ?k=&play=<id> -> that take;
// POST ?k=&id=&t=&part=&parts= with a slice of a WAV -> takes/<id>.flac once all slices are in.
// Slices: the proxy in front rejects bodies over ~1 MB (413), and on a bad connection a small piece is
// cheap to retry. A retried slice just overwrites itself; t (take time) keeps two takes of a line apart.
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
    $t = preg_replace('/[^0-9]/', '', (string)($_GET['t'] ?? '0'));
    $part = (int)($_GET['part'] ?? 0); $parts = (int)($_GET['parts'] ?? 1);
    if ($parts < 1 || $parts > 60 || $part < 0 || $part >= $parts) { http_response_code(400); exit('{"error":"bad part"}'); }
    $stem = sys_get_temp_dir() . '/take-' . md5($id) . "-$t";
    file_put_contents("$stem.$part", file_get_contents('php://input', false, null, 0, 1024 * 1024));
    for ($n = 0; $n < $parts; $n++) if (!is_file("$stem.$n")) exit(json_encode(['ok' => true, 'have' => $n]));
    $wav = '';
    for ($n = 0; $n < $parts; $n++) { $wav .= file_get_contents("$stem.$n"); unlink("$stem.$n"); }
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

if (isset($_GET['play'])) {  // a saved take, to check an old recording before re-recording it
    $f = "$dir/" . str_replace(':', '_', (string)$_GET['play']) . '.flac';
    if (!preg_match('/^[a-z0-9.:-]{1,40}$/', $_GET['play']) || !is_file($f)) { http_response_code(404); exit('{"error":"no take"}'); }
    header('Content-Type: audio/flac');
    header('Content-Length: ' . filesize($f));
    readfile($f);
    exit;
}

$ids = [];
foreach (glob("$dir/*.flac") as $f) $ids[] = str_replace('_', ':', basename($f, '.flac'));
echo json_encode($ids);
