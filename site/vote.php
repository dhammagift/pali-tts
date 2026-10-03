<?php
// Listening-test answers: POST one answer (JSON) -> appended to votes/<round>.jsonl; GET ?round= -> latest state.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
$dir = '/var/www/pali-tts/votes';
$round = preg_replace('/[^a-z0-9_-]/', '', $_GET['round'] ?? '');
if ($round === '') { http_response_code(400); exit('{"error":"round required"}'); }
$file = "$dir/$round.jsonl";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $raw = file_get_contents('php://input', false, null, 0, 4096);
    $v = json_decode($raw, true);
    $ok = is_array($v)
        && preg_match('/^[A-Za-z0-9_.-]{1,40}$/', $v['phrase'] ?? '')
        && in_array($v['kind'] ?? '', ['rating', 'words', 'comment'], true);
    if (!$ok) { http_response_code(400); exit('{"error":"bad answer"}'); }
    if (is_file($file) && filesize($file) > 5 * 1024 * 1024) { http_response_code(507); exit('{"error":"full"}'); }
    $row = [
        't' => date('c'),
        'phrase' => $v['phrase'],
        'kind' => $v['kind'],
        'variant' => substr((string)($v['variant'] ?? ''), 0, 40),
        'value' => is_array($v['value'] ?? null) ? array_slice(array_map('strval', $v['value']), 0, 60) : mb_substr((string)($v['value'] ?? ''), 0, 1000),
    ];
    file_put_contents($file, json_encode($row, JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX);
    exit('{"ok":true}');
}

// GET: fold the log into the latest value per (phrase, kind, variant).
$state = [];
if (is_file($file)) {
    foreach (file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $r = json_decode($line, true);
        if ($r) $state[$r['phrase'] . '|' . $r['kind'] . '|' . $r['variant']] = $r['value'];
    }
}
echo json_encode((object)$state, JSON_UNESCAPED_UNICODE);
