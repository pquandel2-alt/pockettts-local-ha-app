# Modellpaket selbst erzeugen

Das Paket besteht aus den INT8-ONNX-Modellen, dem Tokenizer, `bos_before_voice.npy`, den Referenz-WAVs der Stimmen und einem
`MANIFEST.sha256`. **Veröffentliche es nicht** (zugangsbeschränkte Gewichte).

## 0. Voraussetzungen
1. Auf <https://huggingface.co/kyutai/pocket-tts> mit deinem Konto die Zugangsbedingungen **selbst** lesen und annehmen.
2. Einen Hugging-Face-Token mit **Lese**-Recht erzeugen. Nur für den Export verwenden (z. B. `export HF_TOKEN=…` in der Export-Shell) und danach widerrufen.
3. Docker.

## 1. ONNX-Export (pocket-tts v2.1.0 + Exporter aus PocketTTS.cpp)
Der Exporter des Forks passt zu `pocket-tts` v2.1.0 (neuere Versionen haben die Modulstruktur geändert).
```dockerfile
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir "pocket-tts @ git+https://github.com/kyutai-labs/pocket-tts.git@v2.1.0" onnx onnxruntime huggingface_hub beartype
WORKDIR /work
```
```bash
git clone https://github.com/netai369/PocketTTS.cpp-multilingual && cd PocketTTS.cpp-multilingual && git checkout 3ed176a
docker run --rm -e HF_TOKEN -e HF_HOME=/hf -v $PWD:/work -v hf-cache:/hf IMAGE python export_onnx.py --language german --output-dir /work/models_de
```
Ergebnis in `models_de/`: `*_int8.onnx`, `mimi_encoder.onnx`, `text_conditioner.onnx`, `tokenizer.model` (die INT8-Prüfung des
Exporters kann beim EOS-Logit anschlagen; die tatsächlichen Ausgaben wurden ohne Abbrüche getestet).

## 2. `bos_before_voice.npy`
Der Exporter schreibt die Datei nicht. Sie stammt aus dem Gewicht `flow_lm.bos_before_voice` (`models_de/.cache/tts_german.safetensors`):
```python
import numpy as np; from safetensors import safe_open
with safe_open("models_de/.cache/tts_german.safetensors", framework="pt") as f:
    np.save("models_de/bos_before_voice.npy", f.get_tensor("flow_lm.bos_before_voice").float().numpy().astype(np.float32).reshape(1, 1, 1024))
```

## 3. Referenz-WAVs der Stimmen
Die C++-Engine lädt die offiziellen Stimmzustände (`languages/german/embeddings/<stimme>.safetensors`) nicht, sondern braucht eine WAV je Stimme.
Mit dem offiziellen `pocket-tts` **v3.3.0** (nicht v2.1.0, das bricht deutsche Sätze ab) eine ca. 9 s lange Referenz erzeugen:
```python
import numpy as np, scipy.io.wavfile as wf, huggingface_hub as hf
from pocket_tts.models.tts_model import TTSModel
m = TTSModel.load_model(language="german")
REF = "Dies ist die Stimme für deinen lokalen Sprachassistenten. Ich lese dir die Nachrichten vor, melde den Stand der Waschmaschine und sage dir, wie warm es im Wohnzimmer ist."
for v in ["juergen", "bill_boerst", "charles", "daan", "george", "giovanni", "michael", "paul", "peter_yearsley", "rafael", "stuart_bell"]:
    p = hf.hf_hub_download("kyutai/pocket-tts", f"languages/german/embeddings/{v}.safetensors")
    a = m.generate_audio(m.get_state_for_audio_prompt(p), REF).squeeze().cpu().numpy().astype(np.float32)
    wf.write(f"voices_de/{v}.wav", m.sample_rate, (np.clip(a, -1, 1) * 32767).astype(np.int16))
```

## 4. Paket schnüren
Ordner `models_de/` (nur die in `REQUIRED` von `importer.py` genannten sieben Dateien) und `voices_de/*.wav` anlegen, dann
`tools/make_model_pack.sh <quellordner> <ausgabeordner>` (erzeugt `pockettts-model-pack.tar.gz` mit `MANIFEST.sha256`).
Zum Import siehe `pockettts_local_int8/DOCS.md`, Abschnitt 3.
