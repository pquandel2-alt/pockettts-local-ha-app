# Abnahme auf Home Assistant OS (offen – braucht Zugriff auf die HA-VM)

Alles bis zur Docker-Ebene ist lokal getestet (siehe Abschlussbericht). Folgende Punkte konnten **ohne Zugriff auf die
Home-Assistant-VM nicht geprüft werden** und sind daher noch zu bestätigen:

| # | Prüfung | Vorgehen | Erwartung |
|---|---|---|---|
| 1 | Installation über den App-Store | Ordner `pockettts_local_int8` nach `/addons` (Samba „addons“) → App-Store → ⋮ → Nach Updates suchen → „PocketTTS Local INT8“ installieren | Build ohne Fehler (5–10 min), App erscheint unter „Lokale Apps“ |
| 2 | Modellimport | `pockettts-model-pack.tar.gz` in `addon_configs/<…>_pockettts_local_int8/` legen, App starten | Log: „Import … abgeschlossen (19 Dateien)“, „Bereit: Wyoming-Port 10302, 11 Stimmen“ |
| 3 | Discovery | Einstellungen → Geräte & Dienste | Eintrag „Wyoming Protocol – PocketTTS Local INT8“ (Konfigurieren → Absenden) |
| 4 | Test-Pipeline | Einstellungen → Sprachassistenten → „Assist – PocketTTS Test“ (TTS = pockettts-local-int8, de, juergen) | Pipeline vorhanden, produktive Pipeline unverändert |
| 5 | Sprachausgabe | In der Test-Pipeline Text eingeben („Wie warm ist es im Wohnzimmer?“) | Antwort hörbar, deutsche Zahlen korrekt |
| 6 | Echter Sprachsatellit | Satellit auf die Test-Pipeline stellen, Wake Word sprechen | Antwort über den Satelliten, keine Aussetzer |
| 7 | Latenz auf der HA-VM | App-Log beobachten (`erster Chunk nach … s`) | Vergleichbar mit 0,4–0,5 s (hängt von der CPU-Zuteilung der VM ab) |
| 8 | Neustart | Home Assistant komplett neu starten | App startet von selbst, keine Downloads/Imports im Log |
| 9 | Offline | Internet der HA-VM kurz sperren (Router), Sätze sprechen | Funktioniert weiter (die App braucht kein Internet) |
| 10 | Update/Backup | Backup erstellen und testweise wiederherstellen | Modelle/Stimmen aus `/data` sind wieder da |

Nach erfolgreicher Abnahme (Punkt 6 mit einem echten Satelliten) kann die Ubuntu-TTS-VM als entbehrlich betrachtet werden. **Abschalten/Entfernen
erst nach deiner ausdrücklichen Freigabe.**
