"""Full dataset manifest from the recordings survey + the owner's marks (votes/rec1.jsonl).

Rule: owner's ★/✓ files + unmarked chapter/sutta files with SNR >= 30 dB; never -old, never ✗,
never the old single-rule bu-pm clips (Pc1.mp3 …). Each file gets the SC text range it reads.
Usage: python make_manifest.py > dataset/full.json
"""
import json
import os
import re

SNR_MIN = 30
BU, BI = 'vinaya/pli-tv-bu-pm_root-pli-ms.json', 'vinaya/pli-tv-bi-pm_root-pli-ms.json'
BU_CH = {'pbkrn': (1, 4), 'pbkc1var': (1, 4), 'nid': (5, 7), 'pj': (8, 13), 'ss': (14, 28), 'ay': (29, 32),
         'np1vag': (33, 43), 'np2vag': (44, 53), 'np3vag': (54, 64), 'pd': (159, 164), 'as': (245, 254),
         'sk1vag': (165, 175), 'sk2vag': (176, 186), 'sk3vag': (187, 198), 'sk4vag': (199, 208),
         'sk5vag': (209, 218), 'sk6vag': (219, 228), 'sk7vag': (229, 244)}
for i, (a, b) in enumerate([(65, 75), (76, 85), (86, 95), (96, 105), (106, 115), (116, 125), (126, 135),
                            (136, 147), (148, 158)], 1):
    BU_CH[f'pc{i}vag'] = (a, b)
BI_CH = {'pbkrn': (1, 4), 'nid': (5, 7), 'pj': (8, 17), 'pj1-4': (9, 12), 'ss': (18, 36), 'np1vag': (37, 47),
         'np2vag': (48, 57), 'np3vag': (58, 68), 'pd': (237, 246), 'pd1': (238, 238), 'pd2-8': (239, 245),
         'as': (324, 333), 'sk1vag': (247, 257), 'sk2vag': (258, 267), 'sk3vag': (268, 277), 'sk4vag': (278, 287),
         'sk5vag': (288, 297), 'sk6vag': (298, 307), 'sk7vag': (308, 323)}
PC_BI = [69, 80, 90, 100, 110, 120, 130, 140, 153, 166, 176, 186, 196, 206, 216, 226, 237]
for i in range(16):
    BI_CH[f'pc{i + 1}vag'] = (PC_BI[i], PC_BI[i + 1] - 1)
for k in range(1, 9):
    BI_CH[f'pj{k}'] = (8 + k, 8 + k)
for k in range(1, 11):
    BI_CH[f'np{k}'] = (37 + k, 37 + k)
DN22 = {'11d1dukkham': (17, 18), '11d2samudayo': (19, 19), '11d3nirodho': (20, 20), '11d4maggo': (21, 21), '12': (22, 22)}


def target(path):
    """(text file, range) for a recording, or None when it is not a chapter/sutta file we can map."""
    name = os.path.basename(path)[:-4]
    if '_jiv' in name:
        sid = name.split('_')[0]
        coll = re.match(r'[a-z]+', sid).group()
        sub = re.match(r'[a-z]+\d+', sid).group()
        return f'sutta/{coll}/{sub}/{sid}_root-pli-ms.json', None
    if path.startswith('dn/dn2.9/'):
        part = name.split('-', 1)[1]
        return ('sutta/dn/dn22_root-pli-ms.json', DN22[part]) if part in DN22 else None
    m = re.match(r'(Bu|Bi)-(.+)$', name)
    if m and '-old' not in name:
        table, text = (BU_CH, BU) if m[1] == 'Bu' else (BI_CH, BI)
        return (text, table[m[2]]) if m[2] in table else None
    return None


def marks():
    st = {}
    if os.path.exists('votes/rec1.jsonl'):
        for line in open('votes/rec1.jsonl', encoding='utf-8'):
            r = json.loads(line)
            if r['kind'] == 'rating':
                st[r['phrase']] = r['value']
    return st


def main():
    survey = json.load(open('out/survey/survey.json'))
    mk = marks()
    out = []
    for s in survey:
        p = s['path']
        mark = mk.get(re.sub(r'[^A-Za-z0-9_.-]', '_', p)[:40], '')
        t = target(p)
        if t is None or mark == 'bad' or (mark not in ('best', 'ok') and s['snr_db'] < SNR_MIN):
            continue
        item = {'id': os.path.basename(p)[:-4], 'audio': p, 'text': t[0], 'snr_db': s['snr_db'],
                'min': round(s['dur'] / 60, 1), 'marked': mark}
        if t[1]:
            item['range'] = list(t[1])
        out.append(item)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
