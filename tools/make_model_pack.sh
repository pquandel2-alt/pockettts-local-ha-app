#!/bin/bash
# Erzeugt das Modellpaket (NICHT veroeffentlichen: enthaelt Gewichte des zugangsbeschraenkten kyutai/pocket-tts).
# Nutzung: make_model_pack.sh <quellordner mit models_de/ und voices_de/> [ausgabeordner]
set -euo pipefail
SRC=${1:?Quellordner mit models_de/ und voices_de/}; OUT=${2:-./dist}; W=$(mktemp -d); trap 'rm -rf $W' EXIT
mkdir -p $W/models_de $W/voices_de "$OUT"
for f in flow_lm_flow_int8.onnx flow_lm_main_int8.onnx mimi_decoder_int8.onnx mimi_encoder.onnx text_conditioner.onnx tokenizer.model bos_before_voice.npy; do cp "$SRC/models_de/$f" $W/models_de/; done
cp "$SRC"/voices_de/*.wav $W/voices_de/
cat > $W/models_de/NOTICE.txt <<'TXT'
PocketTTS German model pack (INT8 ONNX export) for the "PocketTTS Local INT8" Home Assistant app.
Source model: kyutai/pocket-tts (package "german"), CC-BY-4.0, access-gated on Hugging Face (acceptance by the account holder required).
Exported with kyutai-labs/pocket-tts v2.1.0 exporter from netai369/PocketTTS.cpp-multilingual @ 3ed176a; bos_before_voice.npy taken from flow_lm.bos_before_voice.
Reference WAVs in voices_de/ were synthesized with the official PyTorch model and the official voice states of the same bundle.
PRIVATE USE ONLY - do not publish this pack. Use must comply with the Kyutai terms (no voice impersonation/cloning without consent).
TXT
( cd $W && find models_de voices_de -type f | sort | xargs sha256sum > MANIFEST.sha256 )
tar --owner=0 --group=0 --numeric-owner --sort=name -C $W -czf "$OUT/pockettts-model-pack.tar.gz" MANIFEST.sha256 models_de voices_de
( cd "$OUT" && sha256sum pockettts-model-pack.tar.gz > pockettts-model-pack.tar.gz.sha256 )
ls -la "$OUT"; cat "$OUT/pockettts-model-pack.tar.gz.sha256"
