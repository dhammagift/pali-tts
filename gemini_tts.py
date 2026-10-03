"""Gemini TTS for Pali: pronunciation rules go to the system instruction, only the Pali text is spoken.

gemini(path, text, model, voice, style) -> seconds of audio (mp3 written to path).
"""
import base64
import json
import os
import subprocess
import urllib.request

KEY = os.environ['GEMINI_TOKEN']
RULES = ('You are a text-to-speech voice reading the Pali canon. Speak ONLY the user text, nothing else. '
         'Use classical Theravada Pali pronunciation: every short a is pronounced and never dropped; '
         'ā ī ū e o are long; ṁ is a velar nasal "ng"; ñ is a palatal "ny"; kh gh ch jh ṭh ḍh th dh ph bh are '
         'aspirated stops (ph is never f, th is never English th); c as in "church", j as in "jar"; '
         'ṭ ḍ ṇ ḷ are retroflex; double consonants are held longer. Calm, clear, unhurried recitation.')


def gemini(path, text, model='gemini-3.8-flash-tts', voice='Achird', style=RULES):
    if os.path.exists(path):
        return None
    body = {'systemInstruction': {'parts': [{'text': style}]},
            'contents': [{'role': 'user', 'parts': [{'text': text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}',
        json.dumps(body).encode(), {'content-type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    pcm = base64.b64decode(r['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', '-',
                    '-b:a', '64k', path], input=pcm, check=True)
    return len(pcm) / 48000
