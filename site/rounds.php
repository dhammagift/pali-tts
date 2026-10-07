<?php
// All listening pages in this folder, newest first, with how many answers each has (votes/<page>.jsonl).
$votes = '/var/www/pali-tts/votes';
$pages = [];
foreach (glob(__DIR__ . '/*.html') as $f) {
    $name = basename($f, '.html');
    if ($name === 'index') continue;
    preg_match('/<h1>([^<]*)/', file_get_contents($f, false, null, 0, 20000), $m);
    $v = "$votes/$name.jsonl";
    $rows = is_file($v) ? file($v, FILE_SKIP_EMPTY_LINES) : [];
    $n = count($rows);
    // file mtimes are reset by deploys: order by the first answer, unanswered pages on top
    $first = $n ? strtotime(json_decode($rows[0], true)['t'] ?? '') : 0;
    $pages[] = ['name' => $name, 'title' => $m[1] ?? $name, 'made' => $first ?: 4e9 + filemtime($f), 'n' => $n,
                'last' => $n ? filemtime($v) : 0];
}
usort($pages, fn($a, $b) => $b['made'] <=> $a['made']);
$h = fn($s) => htmlspecialchars($s, ENT_QUOTES);
?><!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pali TTS — все раунды</title>
<style>
:root { --bg:#fff; --fg:#222; --mute:#777; --line:#e5e5e5; --new:#d35400; --link:#0b63c5; }
@media (prefers-color-scheme: dark) { :root { --bg:#161616; --fg:#e8e8e8; --mute:#999; --line:#333; --new:#f39c12; --link:#6cb4ff; } }
body { background:var(--bg); color:var(--fg); font:16px/1.4 system-ui,sans-serif; margin:0 auto; max-width:760px; padding:16px; }
a { color:var(--link); text-decoration:none; }
li { list-style:none; padding:10px 0; border-bottom:1px solid var(--line); }
ul { padding:0; }
.meta { color:var(--mute); font-size:14px; }
.new { color:var(--new); font-weight:600; }
</style></head><body>
<h1>Pali TTS — все раунды</h1>
<ul>
<?php foreach ($pages as $p): ?>
<li><a href="<?= $h($p['name']) ?>.html"><?= $h($p['title']) ?></a>
<div class="meta"><?= $h($p['name']) ?> ·
<?= $p['n'] ? "ответов {$p['n']}, последний " . date('d.m H:i', $p['last']) : '<span class="new">без ответов</span>' ?></div></li>
<?php endforeach ?>
</ul>
</body></html>
