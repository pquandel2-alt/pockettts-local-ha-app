# Changelog

Alle nennenswerten Änderungen dieser App. Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [1.0.6] - 2026-10-17

### Geändert
- **Standardstimme ist jetzt `george`** (bisher `juergen`). Im Blindtest gegen Supertonic-3, Kokoro und Piper mit acht typischen
  Assist-Antworten bevorzugt. Gemessen (Whisper-Rückerkennung): Wortfehler 1,4 % statt 2,0 % (12 Standard-Antworten), Schlüsselwörter
  in Kalender-Antworten 105/112 statt 102/112; keine verschluckten Wörter.
- Wichtig: Wählt die Assist-Pipeline ausdrücklich eine Stimme (z. B. `juergen`), gilt diese. Zum Wechseln in Home Assistant unter
  *Einstellungen → Sprachassistenten → Pipeline → Text-zu-Sprache* die Stimme auf `george` stellen. Eine bereits gespeicherte
  Option `default_voice` bleibt unverändert.
- `temperature` bleibt 0,7 (0,5 brachte mit `george` mehr Fehler: 3,1 % statt 1,4 %).

## [1.0.5] - 2026-10-17

### Behoben
- **Verschluckte Termine und Fantasiesilben bei Kalender-Antworten** (z. B. „Ich habe 2 Termine gefunden: „Friseur …“ am 18.10. um
  09:00 Uhr; „…“ am 18.10. um 14:00 Uhr.“):
  - Anfragen ohne Streaming wurden als ein einziger langer Block erzeugt; PocketTTS brach dabei oft ab – der letzte Termin fehlte
    in 8 von 12 Durchläufen. Jetzt wird immer satzweise erzeugt (12/12 vollständig).
  - Deutsche Anführungszeichen („…“, »…«) erzeugten vor Titeln Fantasiesilben („Ruh-“, „Duria“); sie werden entfernt.
  - „;“ und „:“ vor einem neuen Satzteil trennen jetzt Sätze (kürzere Abschnitte, natürliche Pause).
  - Kein Satzende mehr nach einem Datum („am 18.10. um 9 Uhr“ wurde in Stücke zerrissen, jedes mit eigener Lautstärke).
  - Gemessen (Whisper-Rückerkennung, Kalender-Antworten): Schlüsselwörter richtig von ca. 75 % auf ca. 92 % (Streaming) bzw.
    von 52 % auf 90 % (ohne Streaming); 12 Standard-Assist-Antworten: verschluckte Wörter 0,6 % → 0 %.
- **Abgeschnittene Satzanfänge:** Das Entfernen der führenden Stille schnitt leise Anlaute (f, s, h) ab („Friseur“ → „Riseur“).
  Schwelle −48 statt −40 dBFS, 150 ms Vorlauf statt 30 ms; die Pause zwischen Sätzen bleibt gleich lang.
- „1 Termin“ → „einen Termin“ statt „eines Termin“; „1 Fenster“ → „ein Fenster“, „1:15 Uhr“ → „ein Uhr fünfzehn“, „1 °C“ → „ein Grad“.

### Hinzugefügt
- **Lautstärkeausgleich** `level_speech` (Standard an): gleicht den Pegel über die ganze Antwort an (langsam, Pausen halten den
  Pegel, ±6 dB). Schwankung des Sprachpegels bei mehrteiligen Antworten von ca. 5,6 auf 4,3 dB; Gesamtlautstärke unverändert.
- 53 automatisierte Tests.

## [1.0.4] - 2026-10-16

### Geändert
- **Klangkorrektur statt reiner Höhenanhebung:** Die Messung gegen klare Sprachausgaben (Supertonic, Piper) zeigte als Ursache des
  dumpfen Klangs gut 10 dB zu viel Dröhnen unter 100 Hz und ca. 8 dB zu wenig Präsenz bei 1,6–3 kHz – die Höhenanhebung aus 1.0.3
  setzte fast nur oberhalb von 3 kHz an. Neue Option `sound_profile` (`klar` = Standard, im Hörtest bevorzugt; `weich`; `aus`)
  gleicht das Langzeitspektrum mit einem linearphasigen FIR (255 Taps, ca. 5 ms) daran an. Pegel unverändert (ca. −20 dBFS mit
  `volume_boost_db` 8), erster Ton ca. 0,5 s, Verständlichkeit unverändert (Whisper-Rückerkennung).
- `treble_boost_db` entfällt (ersetzt durch `sound_profile`); ein gespeicherter alter Wert wird ignoriert.
- 49 automatisierte Tests.

## [1.0.3] - 2026-10-16

### Hinzugefügt
- **Klangaufbereitung** gegen leisen und dumpfen Klang (Hörtest: Variante „lauter + Höhen +8 dB“ bevorzugt):
  - `volume_boost_db` (Standard 8): Verstärkung mit weichem Begrenzer; Pegel von ca. −26 auf ca. −19 dBFS.
  - `treble_boost_db` (Standard 8): linearphasige Höhenanhebung ab ca. 2 kHz (voll ab 4 kHz); Energie über 3 kHz von ca. 0,5 % auf ca. 3 %
    (Referenzstimmen 2–3 %).
  - Läuft im Streaming nahtlos je Satz, ca. 1,3 ms Verzögerung, kein messbarer Einfluss auf die Verständlichkeit (Whisper-Rückerkennung).
- 5 neue Tests (47 gesamt).

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
