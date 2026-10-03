"""Check tts_server.prune_cache without starting the server: size cap and the low-disk guard."""
import os
import re
import shutil
import tempfile
import time

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tts_server.py'), encoding='utf-8').read()
ns = {'os': os, 'shutil': shutil}
exec(re.search(r'def prune_cache.*?return removed\n', src, re.S).group(), ns)
prune_cache = ns['prune_cache']


def fresh():
    d = tempfile.mkdtemp()
    for i in range(10):  # 10 x 100 KB, 0.mp3 the least recently used
        p = os.path.join(d, f'{i}.mp3')
        open(p, 'wb').write(b'x' * 100 * 1024)
        os.utime(p, (time.time() + i, time.time() + i))
    return d


d = fresh()
assert prune_cache(d, 500 * 1024) == 6 and sorted(os.listdir(d)) == ['6.mp3', '7.mp3', '8.mp3', '9.mp3']
d = fresh()
assert prune_cache(d, 10 ** 9, shutil.disk_usage(d).free + 300 * 1024) == 4  # disk short by 300 KB
print('ok')
