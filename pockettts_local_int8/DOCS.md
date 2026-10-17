# PocketTTS Local INT8 – Dokumentation

Offline-Sprachausgabe (Text-to-Speech) auf Deutsch für Home Assistant Assist. Die App enthält die native
PocketTTS-C++-Engine (ONNX Runtime, nur CPU; Hauptmodell FP32, übrige Modelle INT8) und einen Wyoming-Dienst, der Audio **schon während der Erzeugung**
an Home Assistant streamt. Es werden keine Cloud-Dienste verwendet und nach dem einmaligen Modellimport sind keine
Downloads nötig.

> **Stand:** Version 1.0.4, Stufe *experimental*. Lokal (Docker) umfangreich getestet; die Abnahme auf Home Assistant OS
> samt Sprachsatellit steht noch aus (siehe Abschnitt „Abnahme“).

## 1. Voraussetzungen

- Home Assistant OS/Supervised, Architektur **amd64**, Home Assistant ≥ 2024.1.
- Das **Modellpaket** `pockettts-model-pack.tar.gz` (Abschnitt 3). Es enthält zugangsbeschränkte Gewichte von
  `kyutai/pocket-tts` (CC-BY-4.0, auf Hugging Face nur nach Zustimmung zugänglich). Es ist **nicht** Teil der App und darf
  nicht veröffentlicht werden. Der Hugging-Face-Token wird im Betrieb **nicht** benötigt.

## 2. App installieren

### Variante A – lokale App (empfohlen für den Test)
1. Installiere die Add-on **Samba share** (oder **Advanced SSH & Web Terminal**) in Home Assistant.
2. Kopiere den Ordner `pockettts_local_int8` in die Freigabe **`addons`** (Pfad `/addons/pockettts_local_int8`).
3. *Einstellungen → Apps (Add-ons) → App-Store →* ⋮ *→ Nach Updates suchen.* Unter **Lokale Apps** erscheint
   „PocketTTS Local INT8“ → **Installieren**. Home Assistant baut das Image dabei selbst (ca. 5–10 Minuten, braucht Internet
   nur für den Build).

### Variante B – über das Repository (App-Store)
*Einstellungen → Apps → App-Store → ⋮ → Repositories* → die URL dieses GitHub-Repositories eintragen → *Hinzufügen*.
Danach erscheint „PocketTTS Local INT8“ im Store. Home Assistant baut das Image selbst (5–10 Minuten).

## 3. Modellpaket importieren (einmalig)

Das Paket (`pockettts-model-pack.tar.gz`, ca. 236 MB ab App 1.0.2) ist **nicht** in diesem Repository und nicht im Release enthalten (zugangsbeschränkte Gewichte). Wie du es selbst erzeugst: `docs/MODEL_PACK.md` im Repository. Es enthält die INT8-Modelle, das
Hauptmodell zusätzlich in FP32 (`flow_lm_main.onnx`), den Tokenizer, `bos_before_voice.npy`, die Referenz-Stimmen und ein `MANIFEST.sha256`.
Die App importiert es **automatisch** – beim Weg über den Ordner ist kein Neustart nötig. Wähle **einen** Weg:

1. **App-Konfigurationsordner (empfohlen):** Kopiere die Datei in die Samba-Freigabe **`addon_configs`** in den Ordner dieser App
   (Name endet auf `_pockettts_local_int8`). Innerhalb der App ist das `/config`.
2. **/share:** Lege die Datei nach `/share/pockettts/pockettts-model-pack.tar.gz` (Samba-Freigabe `share`).
3. **LAN-Link (einmalig):** Stelle die Datei in deinem Netzwerk bereit (z. B. `python3 -m http.server`) und trage unter
   *Konfiguration* `import_url` (und möglichst `import_sha256`) ein und **starte die App neu** (Optionen werden beim Start gelesen).
   Wird nur genutzt, solange keine Modelle oder noch kein FP32-Hauptmodell installiert sind. Danach beide Felder wieder leeren.

Der Import prüft **jede Datei gegen das Manifest** (SHA-256), lehnt Pakete mit unbekannten Dateinamen, Verzeichnisausbrüchen
oder Links ab und schreibt atomar nach `/data`. Danach liegen Modelle, Stimmen und Caches dauerhaft in `/data`
(überlebt Neustart, Update und Backup). Die Quelldatei kannst du danach löschen. Im Log siehst du
`Import … abgeschlossen`. Fehlen Modelle oder ist ein Paket defekt, steht im Log eine **verständliche Meldung**, und die App
wartet, bis ein gültiges Paket auftaucht.

### Umstieg vom alten Modellpaket (bis 1.0.1, ca. 93 MB)
Das alte Paket enthält das Hauptmodell nur in INT8. Version 1.0.2 läuft damit weiter wie bisher (INT8) und meldet im Log
„Das installierte Modellpaket enthaelt noch kein FP32-Hauptmodell …“. Stelle das **neue** Paket auf einem der drei Wege oben bereit
(eine alte Datei im Ordner einfach überschreiben). Die App erkennt es im laufenden Betrieb, prüft und übernimmt es und startet die Engine
selbst mit FP32-Hauptmodell neu (Log: „Neues Modellpaket … uebernommen“, danach „Starte PocketTTS-Engine (Hauptmodell FP32 …)“).
Beim LAN-Link nach dem Eintragen die App einmal neu starten.

## 4. In Home Assistant einrichten

- **Automatisch:** Die App meldet sich per Supervisor-Discovery als **Wyoming Protocol**. Unter *Einstellungen → Geräte & Dienste*
  erscheint „PocketTTS Local INT8“ → **Konfigurieren**.
- **Manuell:** *Integration hinzufügen → Wyoming Protocol* → Host `<IP deiner Home-Assistant-Instanz>` oder der interne App-Hostname,
  Port **10302**. (Der Port ist standardmäßig veröffentlicht; unter *Netzwerk* kannst du ihn deaktivieren, Discovery
  funktioniert dann weiter intern.)
- **Test-Pipeline (ändert deine produktive Pipeline nicht):** *Einstellungen → Sprachassistenten → Assistent hinzufügen*,
  Name z. B. „Assist – PocketTTS Test“. Spracherkennung, Konversationsagent und Wake Word wie in deiner Pipeline wählen,
  bei **Text-to-Speech** „pockettts-local-int8“, Sprache **Deutsch**, Stimme z. B. **george**. Die bestehende Edge-TTS bleibt unberührt.

## 5. Stimmen

`george` (Standard, im Blindtest bevorzugt), `juergen`, `bill_boerst`, `charles`, `daan`, `giovanni`, `michael`, `paul`, `peter_yearsley`, `rafael`,
`stuart_bell` – alle erscheinen in der Stimmenauswahl. Die C++-Engine klont jede Stimme aus einer Referenz-WAV; die
Stimm- und KV-Caches (`/data/voices_de/.cache`) hängen vom **Inhalt** der WAV und der Modelldateien ab und aktualisieren sich
deshalb zuverlässig, sobald sich eine Stimme ändert. *Eigene Stimmen:* Lege WAV-Dateien (mono, ca. 5–15 s) in den
Konfigurationsordner unter `voices/`. Sie werden beim Start übernommen. Beachte die Nutzungsbedingungen des Modells
(keine Stimmen ohne Einwilligung klonen).

## 6. Konfiguration

| Option | Standard | Wirkung |
|---|---|---|
| `language` | `de` | Das deutsche Paket unterstützt nur `de`. |
| `default_voice` | `george` | Stimme, wenn Home Assistant keine anfordert. Wählt die Assist-Pipeline eine Stimme aus, gilt diese – zum Wechseln die Stimme in der Pipeline umstellen. |
| `threads` | `3` | ONNX-Runtime-Threads. Mit FP32-Hauptmodell ist 3 der gemessene Kompromiss, mit INT8 reichen 2. Bestehende Installationen behalten ihren Wert – nach dem Update auf 3 stellen. |
| `main_model` | `fp32` | Hauptmodell (`flow_lm_main`) in `fp32` (deutlich verständlicher) oder `int8` (schneller, verschluckt öfter Wörter). `fp32` braucht das Modellpaket ab 1.0.2, sonst wird `int8` genutzt. |
| `streaming` | `true` | Audio während der Erzeugung senden. Aus: erst komplett erzeugen, dann senden. |
| `first_chunk` / `max_chunk` | `2` / `4` | Frames (je 80 ms) des ersten / weiterer Chunks. `max_chunk` ≥ `first_chunk`. |
| `prebuffer_ms` | `150` | Vorpuffer vor dem ersten gesendeten Block (verhindert kurze Lücken). |
| `lead_in_ms` | `0` | Stille, die die Engine voranstellt (Adapter schneidet führende Stille ab). |
| `warmup` | `true` | Testsatz nach dem Start, damit die erste Anfrage schnell ist. |
| `preload_voices` | `true` | Caches aller Stimmen beim Start anlegen (nur beim ersten Mal ca. 1 Minute). |
| `normalize_text` | `true` | Zahlen, Uhrzeiten, Einheiten, Abkürzungen in Wörter umwandeln. |
| `ort_spinning` | `false` | ONNX-Threads aktiv warten lassen (mehr CPU, kaum schneller). |
| `temperature` | `0.7` | Zufälligkeit der Stimmerzeugung (0,1–1,0). 0,3 und 0,5 brachten keinen messbaren Vorteil. |
| `volume_boost_db` | `8` | Verstärkung in dB (0–20) mit weichem Begrenzer. PocketTTS ist von sich aus leise (ca. −26 dBFS); 8 dB ergeben übliche ca. −19 dBFS. 0 = aus. |
| `sound_profile` | `klar` | Klangkorrektur gegen den dumpfen Klang: PocketTTS hat gut 10 dB zu viel Dröhnen unter 100 Hz und ca. 8 dB zu wenig Präsenz bei 1,6–3 kHz (gemessen gegen Supertonic/Piper). `klar` gleicht das an und ist oben etwas heller (im Hörtest bevorzugt), `weich` mit zurückhaltenderen Höhen, `aus` ohne Korrektur. Gilt für alle Stimmen gleich (alle haben dasselbe Spektrum). |
| `level_speech` | `true` | Lautstärkeausgleich über die ganze Antwort: PocketTTS erzeugt jeden Satz mit eigenem Pegel (gemessen bis ca. 5 dB Unterschied) und wird in langen Sätzen oft leiser. Langsam geregelt (ca. 0,5 s), Pausen halten den Pegel; die Gesamtlautstärke bleibt gleich. |
| `log_level` | `info` | `debug` zeigt auch die gesprochenen Texte. |
| `import_url`, `import_sha256` | – | Einmaliger Modellimport per LAN-Link (nach dem Eintragen App neu starten). |

Ungültige Werte lehnt der Supervisor ab; die App prüft zusätzlich (z. B. `max_chunk` ≥ `first_chunk`) und meldet den Fehler im Log.

## 7. Textnormalisierung

PocketTTS spricht rohe Ziffern schlecht aus („21 Grad“ wurde zu „kast Grad Grad“). Darum wandelt die App um:
`21 Grad` → *einundzwanzig Grad*, `12,5 Grad` → *zwölf Komma fünf Grad*, `18:35 Uhr` / `18 Uhr 35` → *achtzehn Uhr fünfunddreißig*,
`65 %` → *fünfundsechzig Prozent*, `7 °C` → *sieben Grad Celsius*, `1.250 W` → *eintausendzweihundertfünfzig Watt*,
`14.05.2026` → *vierzehnten Mai …*, `z. B.` → *zum Beispiel*. Normale Sätze bleiben unverändert (Tests im Image:
`/opt/app/tests`).

## 8. Gemessene Leistung (lokaler Test, Docker auf Ubuntu-VM mit i5-12450H, 4 vCPUs)

**Ab 1.0.2 (FP32-Hauptmodell, Standard):** 12 typische Assist-Antworten, Wyoming-Streaming-Eingabe wie Home Assistant, Rückerkennung mit Whisper (small).

| | Verschluckte Wörter | Sätze mit Auslassung | Erster Chunk P50 / P95 | RTF P50 / max | RAM |
|---|---|---|---|---|---|
| **Hauptmodell FP32, `threads` 3** (1.0.2, 96 Proben) | **0–0,4 %** | 0–2 % | 0,56 / 0,67 s | 0,60 / 0,78 | ca. 570 MB |
| Hauptmodell FP32, `threads` 2 | 0,2–0,4 % | 2–4 % | 0,62 / 0,80 s | 0,64 / 0,91 | |
| Alles INT8 (bis 1.0.1), `threads` 2, Mittel aus 11 Stimmen | ca. 8 % (4–13 %) | ca. 25 % | 0,39 / 0,55 s | 0,42 / 0,71 | ca. 390 MB |
| Alles FP32 | 0,5–0,7 % | 5–7 % | 0,70 / 0,88 s | 0,75 / 1,07 | |

Die INT8-Quantisierung des Hauptmodells (`flow_lm_main`) ist die Ursache für die verschluckten Wörter: das Modell nuschelt Wörter, statt
sie auszulassen (die Audiodauer bleibt gleich, deshalb lässt sich das nicht automatisch erkennen). Temperatur 0,3/0,5, Rauschbegrenzung,
mehr Flow-Schritte, spätere EOS-Erkennung oder das Aufteilen an Kommas brachten mit INT8 keine Verbesserung.

**Bis 1.0.1 (alles INT8):** 6 deutsche Testsätze, 5 Wiederholungen nach Warmup, echter Wyoming-Client, Zeit bis zum **ersten Audio-Chunk** (Audio ist ab da hörbar).

| | Erster Chunk P50 / P95 | RTF (P50) | CPU beim Sprechen | RAM |
|---|---|---|---|---|
| Standard (`threads` 2, kein Spinning) | 0,40 / 0,55 s | 0,44 | ca. 1,5 Kerne | ca. 390 MB |
| `threads` 3 | 0,32 / 0,55 s | 0,39 | ca. 1,8 Kerne | ca. 370 MB |
| `threads` 4 | 0,33 / 0,44 s | 0,37 | ca. 2,4 Kerne | ca. 380 MB |
| Standard unter Fremdlast (2 Kerne ausgelastet) | 0,47–0,50 / 0,70 s | 0,48–0,51 | ca. 1,5 Kerne | ca. 460 MB |

- Im Leerlauf: 0,0 % CPU. Nach einem Neustart ist Wyoming nach ca. 1 s erreichbar, die erste Anfrage liefert nach ca. 0,5 s Audio.
- `threads` 1 und 2 sind laut Engine-Code identisch (je 1 Thread für Generator und Decoder); erst ab 3 gibt es mehr Parallelität.
- Auf der Home-Assistant-VM (7 vCPUs, geteilter Proxmox-Host) können die Werte abweichen. Liegt der RTF dort nahe 1 (Aussetzer), `threads` auf 4 erhöhen oder `main_model: int8` wählen.

## 9. Bekannte Einschränkungen (ehrlich gemessen)

- **INT8-Hauptmodell:** Mit `main_model: int8` (oder dem alten Modellpaket) verschluckt bzw. nuschelt PocketTTS rund 8 % der Wörter,
  besonders in längeren Sätzen mit Zahlen; die Stimme `juergen` ist dabei am anfälligsten. Mit FP32-Hauptmodell (Standard ab 1.0.2) unter 1 %.
- **Streuung:** Die Stimmerzeugung ist zufallsgesteuert (Temperatur 0,7); einzelne Wörter können weiterhin leicht anders klingen.
- **Eine Synthese zur Zeit:** Gleichzeitige Anfragen werden nacheinander bearbeitet (8 parallele Anfragen: alle erfolgreich, die Wartezeit wächst).
- **Stimmklone:** Die Stimmen sind aus Referenz-WAVs rekonstruiert und können leicht vom offiziellen Stimmzustand abweichen.

## 10. Betrieb, Ressourcen, Sicherheit

- Der C++-Server lauscht **nur auf Loopback (127.0.0.1)** im Container; nur der Wyoming-Port 10302 ist erreichbar.
- Es läuft genau **eine** Synthese zur Zeit (weitere warten in der Schlange). Bricht ein Client ab, wird die Synthese sofort beendet. Fehler der Engine meldet der Adapter als Wyoming-`Error`-Event, und Anfragen während eines Engine-Neustarts warten bis zu 10 s.
- Die Engine wird bei einem Absturz automatisch mit Backoff neu gestartet; der Healthcheck prüft einen Wyoming-Describe-Rundlauf mit Stimmen; der Supervisor-Watchdog überwacht den Port.
- Logs enthalten keine Zugangsdaten und standardmäßig keine gesprochenen Texte.
- Backups enthalten Modelle und Stimmen (die sich ohne dein Modellpaket nicht wiederherstellen ließen), nicht aber die regenerierbaren Caches.

## 11. Fehlersuche

| Meldung / Symptom | Ursache und Lösung |
|---|---|
| „Es sind noch keine Modelldateien vorhanden …“ | Modellpaket importieren (Abschnitt 3). Die App wartet und importiert automatisch. |
| „… noch kein FP32-Hauptmodell …“ / „… enthaelt kein FP32-Hauptmodell (altes Modellpaket)“ | Altes Paket (bis 1.0.1). Neues Paket bereitstellen (Abschnitt 3, „Umstieg“). Bis dahin läuft die App mit INT8. |
| Antworten verschlucken/nuscheln Wörter | Im Log muss „Hauptmodell FP32“ stehen. Steht dort INT8: neues Modellpaket importieren bzw. `main_model` auf `fp32` stellen. |
| „Modellimport abgelehnt: Pruefsumme stimmt nicht …“ | Paket beschädigt/manipuliert; neu kopieren. |
| „MANIFEST.sha256 fehlt …“ | Es ist nicht das richtige Paket. |
| App läuft, aber in Home Assistant keine Stimmen | Integration neu laden; Log prüfen (Healthcheck/Stimmen). |
| Erste Antwort nach dem Start langsam | Warmup abwarten (Log „Warmup …“); `warmup` und `preload_voices` aktiv lassen. |
| Kurze Aussetzer bei Satelliten | `prebuffer_ms` auf 250–400 erhöhen. |
| Mal laut, mal leise | `level_speech` aktiv lassen (Standard). |
| Titel in Anführungszeichen / Aufzählungen mit „;“ werden verschluckt | Ab 1.0.5 behoben: Anführungszeichen werden entfernt, „;“ und „:“ trennen Satzteile, auch bei Anfragen ohne Streaming wird satzweise erzeugt. |
| Zu leise / dumpf | `volume_boost_db` erhöhen (z. B. 10–12); `sound_profile` auf `klar`. Klingt es zu scharf: `weich`. Verzerrt: `volume_boost_db` senken. |

## 12. Updates und Backup

- **Update:** Neue Version in `config.yaml` (`version`) eintragen, Ordner ersetzen, *Nach Updates suchen* → *Aktualisieren*. Modelle bleiben in `/data` erhalten, es gibt keinen erneuten Import
  (Ausnahme: Umstieg auf das Modellpaket ab 1.0.2, siehe Abschnitt 3).
- **Engine aktualisieren:** `POCKETTTS_CPP_COMMIT` im `Dockerfile` ändern und alle Patches in `patches/` neu gegen den neuen Stand prüfen.
- **Backup:** Standard-Backup von Home Assistant (enthält `/data`). Zusätzlich das Modellpaket sicher (privat) aufbewahren.

## 13. Abnahme (noch offen)

Siehe `ABNAHME.md` im Projektordner: Installation auf HAOS, Wyoming-Anbindung, Test-Pipeline, echter Sprachsatellit,
Offline-Test und Neustart auf der Home-Assistant-VM.

## 14. Lizenzen

App-Code: privat. PocketTTS.cpp: MIT. Modell `kyutai/pocket-tts`: CC-BY-4.0 mit Zugangsbedingungen (Verbote u. a.
für Stimmimitation ohne Einwilligung). ONNX Runtime: MIT. Weitere Komponenten: siehe `requirements.txt`.
