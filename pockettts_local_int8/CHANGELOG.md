# Changelog

Alle nennenswerten Änderungen dieser App. Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [1.0.2] - 2026-10-16

### Behoben
- **Verschluckte/genuschelte Wörter:** Ursache war die INT8-Quantisierung des Hauptmodells (`flow_lm_main`). Neue Option
  `main_model` (Standard `fp32`) lädt nur dieses Modell in FP32, die übrigen bleiben INT8. Gemessen (Whisper-Rückerkennung,
  12 Assist-Antworten): verschluckte Wörter von ca. 8 % auf 0–0,4 %, Sätze mit Auslassung von ca. 25 % auf 0–2 %.
  Kosten: erster Ton ca. 0,56 s statt 0,4 s, ca. 180 MB mehr RAM.
- Hart getrennte Clients (z. B. Healthcheck) erzeugen keine Tracebacks „Task exception was never retrieved“ mehr im Log.

### Geändert
- Neues Modellpaket (Format 2, ca. 236 MB) mit zusätzlichem `flow_lm_main.onnx` (FP32). Das alte Paket funktioniert weiter (dann INT8).
  Ein neues Paket wird im laufenden Betrieb erkannt, übernommen und die Engine automatisch mit FP32 neu gestartet.
- Standard für `threads` ist jetzt 3 (gemessener Kompromiss mit FP32). Bestehende Installationen behalten ihren Wert.
- Engine-Patch `0003-fp32-main-model-option.patch` (Umgebungsvariable `PTT_MAIN_PRECISION`).
- Doku: `import_url` wird nur beim Start gelesen – nach dem Eintragen die App neu starten.

## [1.0.1] - 2026-10-15

### Behoben
- Beim Warten auf das Modellpaket meldete der Container „unhealthy“; der Supervisor wartete deshalb 120 s auf den Start
  („Timeout while waiting for app … to start“). Das Warten ist jetzt ein gesunder Zustand, und der Wyoming-Port ist
  schon offen (Platzhalter-Server), sodass auch der Watchdog nicht neu startet.
- Docker-Healthcheck prüft beim Start alle 3 s (`--start-interval`), die App gilt nach wenigen Sekunden als gesund.
- Die Hinweiszeile im Log ist kürzer (Warnung statt Fehler, nur die ersten fehlenden Dateien).

## [1.0.0] - 2026-10-15

### Hinzugefügt
- Erste Version als Home-Assistant-App (nur amd64).
- Native Engine PocketTTS.cpp (Commit `3ed176a`) mit ONNX Runtime 1.23.2, deutsches Modellpaket, INT8, CPU-only.
- Echtes Audio-Streaming (Wyoming `AudioChunk`s direkt aus der Inferenz), 150-ms-Vorpuffer, Wyoming-Streaming-Eingabe
  (`SynthesizeStart/Chunk/Stop`).
- Deutsche Textnormalisierung (Zahlen, Uhrzeiten, Dezimalzahlen, Einheiten, Prozent, Abkürzungen, Datum).
- Elf deutsche Stimmen (Standard `juergen`), eigene Referenz-WAVs optional über den App-Konfigurationsordner.
- Sicherer, einmaliger Modellimport (Datei, `/share` oder LAN-URL) mit Pflicht-Manifest und SHA-256-Prüfung; danach vollständig offline.
- Wyoming-Discovery über den Supervisor, Healthcheck (Describe-Rundlauf), Watchdog, Neustart der Engine mit Backoff.
- Konfiguration über die App-Oberfläche (Threads, Chunk-Größen, Vorpuffer, Warmup, Log-Level, Normalisierung, …).

### Bekannt
- Die Engine wurde lokal (Docker auf Ubuntu) getestet, noch nicht auf Home Assistant OS (siehe DOCS.md, Abnahme).
