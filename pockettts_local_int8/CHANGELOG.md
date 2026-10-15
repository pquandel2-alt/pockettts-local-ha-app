# Changelog

Alle nennenswerten Änderungen dieser App. Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

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
