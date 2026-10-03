"""Kaggle GPU job: AI4Bharat Indic Parler-TTS (Sanskrit voices) reading Pali test phrases in Devanagari."""
import os
import subprocess
import sys

W = '/kaggle/working'
TEXTS = {
 "c9": "इध भिक्खु विविच्चेव कामेहि विविच्च अकुसलेहि धम्मेहि सवितक्कं सविचारं विवेकजं पीतिसुखं पठमं झानं उपसम्पज्ज विहरति.",
 "c14": "एवं मे सुतं , एकं समयं भगवा सावत्थियं विहरति जेतवने अनाथपिण्डिकस्स आरामे.",
 "c1": "या तेसं तेसं सत्तानं तम्हि तम्हि सत्तनिकाये जाति सञ्जाति ओक्कन्ति अभिनिब्बत्ति खन्धानं पातुभावो आयतनानं पटिलाभो.",
 "c2": "चक्खुसम्फस्सो अनत्ताति पस्सति, यम्पिदं चक्खुसम्फस्सपच्चया उप्पज्जति वेदयितं सुखं वा दुक्खं वा अदुक्खमसुखं वा.",
 "c4": "चक्खुञ्च पटिच्च रूपे च उप्पज्जति चक्खुविञ्ञाणं, तिण्णं सङ्गति फस्सो.",
 "c10": "यायं तण्हा पोनोब्भविका नन्दिरागसहगता तत्रतत्राभिनन्दिनी, सेय्यथिदं , कामतण्हा, भवतण्हा, विभवतण्हा.",
 "c11": "मनोपुब्बङ्गमा धम्मा, मनोसेट्ठा मनोमया; मनसा चे पदुट्ठेन, भासति वा करोति वा; ततो नं दुक्खमन्वेति, चक्कंव वहतो पदं."
}
VOICES = ['Aryan', 'Vasudha']


def main():
    subprocess.run('pip install -q git+https://github.com/huggingface/parler-tts.git soundfile', shell=True, check=True)
    import soundfile as sf
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    dev = 'cuda'
    model = ParlerTTSForConditionalGeneration.from_pretrained('ai4bharat/indic-parler-tts').to(dev)
    tok = AutoTokenizer.from_pretrained('ai4bharat/indic-parler-tts')
    dtok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    os.makedirs(f'{W}/out', exist_ok=True)
    for voice in VOICES:
        desc = (f"{voice} speaks slowly and clearly in a calm, steady voice, reciting a sacred text. "
                "The recording is of very high quality with no background noise.")
        d = dtok(desc, return_tensors='pt').to(dev)
        for cid, text in TEXTS.items():
            p = tok(text, return_tensors='pt').to(dev)
            torch.manual_seed(0)
            gen = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                                 prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
            sf.write(f'{W}/out/{cid}.parler_{voice.lower()}.wav', gen.cpu().numpy().squeeze(), model.config.sampling_rate)
            print(voice, cid, flush=True)


try:
    main()
except Exception as e:  # keep the reason where it is easy to fetch
    import traceback
    open(f'{W}/error.txt', 'w').write(traceback.format_exc())
    raise
