"""Stress marks for the Russian sentences before Chatterbox reads them. Chatterbox wants a combining acute after the
stressed vowel (its own RussianTextStresser is not installable on Kaggle's Python, so it read without stress - every
clip of the first dataset had stress errors). ruaccent (Silero team) puts '+' before the vowel; converted here.
Sentences ruaccent fails on are left out.
Usage (on f3): /root/venv-ml/bin/python stress_ru.py in.txt out.txt
"""
import re
import sys

from ruaccent import RUAccent

acc = RUAccent()
acc.load(omograph_model_size='turbo3.1', use_dictionary=True)
out, failed = [], 0
for line in open(sys.argv[1], encoding='utf-8').read().split('\n'):
    if not line.strip():
        continue
    try:
        out.append(re.sub(r'\+(\w)', lambda m: m.group(1) + '́', acc.process_all(line)))
    except Exception:  # its homograph model breaks on some inputs (missing token_type_ids)
        failed += 1
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(out), 'stressed,', failed, 'skipped')
