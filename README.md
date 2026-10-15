# PocketTTS Local – Home Assistant App

Offline-Sprachausgabe auf Deutsch für Home Assistant Assist: native **PocketTTS.cpp**-Engine (ONNX Runtime, INT8, nur CPU),
echtes Audio-Streaming über das **Wyoming**-Protokoll, deutsche Textnormalisierung, elf Stimmen. Nur **amd64**.

> **Wichtig:** Die Modellgewichte (`kyutai/pocket-tts`, Paket `german`) sind bei Hugging Face zugangsbeschränkt und
> **nicht Teil dieses Repositorys, des Releases oder des Images**. Du brauchst ein eigenes Modellpaket
> (Anleitung: [`docs/MODEL_PACK.md`](docs/MODEL_PACK.md)) und musst die Bedingungen von Kyutai selbst akzeptieren.

## Installation
1. In Home Assistant: *Einstellungen → Apps → App-Store → ⋮ → Repositories* → URL dieses Repositorys hinzufügen
   (oder den Ordner `pockettts_local_int8` nach `/addons` kopieren).
2. App „PocketTTS Local INT8“ installieren (Build ca. 5–10 Minuten, braucht dabei Internet).
3. Modellpaket importieren (einmalig) und starten – Details in [`pockettts_local_int8/DOCS.md`](pockettts_local_int8/DOCS.md).

Der Status *experimental* ist Absicht: Die App wurde lokal (Docker) umfassend getestet; die Abnahme auf Home Assistant OS
steht aus ([`ABNAHME.md`](pockettts_local_int8/ABNAHME.md)).

## Inhalt
- `pockettts_local_int8/` – die App (Dockerfile mit gepinntem Multi-Stage-Build, Patches, Python-Adapter, Tests, Übersetzungen)
- `docs/MODEL_PACK.md` – Modellpaket selbst erzeugen
- `tools/` – lokale Testumgebung (Supervisor-Mock), Schema-Validierung, Paketskripte

## Tests
`docker build -t pockettts-local pockettts_local_int8 && docker run --rm --entrypoint /opt/app/tests/run_tests.sh pockettts-local`

## Lizenzen
PocketTTS.cpp: MIT · ONNX Runtime: MIT · Modell `kyutai/pocket-tts`: CC-BY-4.0 mit Zugangsbedingungen (u. a. Verbot der
Stimmimitation ohne Einwilligung). Für den Code dieses Repositorys ist noch keine Lizenz festgelegt (alle Rechte vorbehalten).
