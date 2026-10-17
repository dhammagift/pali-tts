"""Fetch every file of a public Google Drive folder and prove none is lost (owner 2026-10-17: gdown.download_folder
silently dropped 11 of Miles's 100 takes and failed on the next folder). Lists the folder's ids, downloads each one
missing in DEST straight from drive.usercontent, checks it is a WAV, exits 1 unless DEST holds every listed file.
Miles's takes come as <k>.<anything>.wav; in a DEST named <a>-<b> take k is saved as <k>.<a+k-1>.wav (its script line).
Usage: /root/.local/bin/uvx --with gdown python fetch_drive.py <folder url> <dest dir>
"""
import os
import re
import sys
import urllib.request

import gdown

URL, DEST = sys.argv[1:3]
os.makedirs(DEST, exist_ok=True)
listed = gdown.download_folder(URL, skip_download=True, use_cookies=False, quiet=True)
first = re.fullmatch(r'(\d+)-\d+', os.path.basename(os.path.normpath(DEST)))
bad, lost = [], []


def target(name):
    k = re.match(r'(\d+)\.', name)
    return f'{k[1]}.{int(first[1]) + int(k[1]) - 1}.wav' if first and k and name.endswith('.wav') else name


for f in listed:
    path = os.path.join(DEST, target(os.path.basename(f.path)))
    if not os.path.exists(path):
        urllib.request.urlretrieve(f'https://drive.usercontent.google.com/download?id={f.id}&export=download&confirm=t', path)
    if path.endswith('.wav') and open(path, 'rb').read(4) != b'RIFF':
        bad.append(os.path.basename(path))
        os.remove(path)
    if not os.path.exists(path):
        lost.append(os.path.basename(f.path))
# every listed file by its own name, not a count: a count passes with duplicates in place of the lost ones
print(f'listed {len(listed)}, lost {lost}, broken {bad}')
sys.exit(1 if bad or lost else 0)

