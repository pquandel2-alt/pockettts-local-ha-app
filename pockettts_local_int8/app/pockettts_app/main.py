"""Einstiegspunkt der App: Optionen -> Modellimport -> Engine -> Wyoming-Server -> Discovery/Warmup; sauberes Beenden bei SIGTERM."""
import asyncio, logging, os, signal, sys
from . import discovery, importer, settings as cfg, wyoming_server
from .engine import Engine

log = logging.getLogger("app")
VERSION = os.environ.get("APP_VERSION", "dev")
WYOMING_PORT = int(os.environ.get("WYOMING_PORT", "10302"))

HOWTO = ("Keine Modelldateien gefunden - die App wartet. Modellpaket 'pockettts-model-pack.tar.gz' in den App-Konfigurationsordner "
         "(Samba 'addon_configs') oder nach /share/pockettts/ legen, oder import_url setzen. Import erfolgt automatisch (DOCS.md, Abschnitt 3).")

WAITING_FLAG = os.environ.get("WAITING_FLAG", "/run/pockettts_waiting")

def set_waiting(on):
    """Marker fuer den Healthcheck: Warten auf das Modellpaket ist ein gueltiger, gesunder Zustand (kein Neustart-Loop)."""
    try:
        if on: open(WAITING_FLAG, "w").close()
        else: os.remove(WAITING_FLAG)
    except OSError: pass

def setup_logging(level):
    logging.basicConfig(level=getattr(logging, level.upper()), format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S", stream=sys.stdout)

async def wait_for_models(s, stop):
    last_hint = 0.0
    while not stop.is_set():
        inst = importer.check_install()
        if inst.ok: return True
        try:
            msg = await asyncio.get_running_loop().run_in_executor(None, importer.try_import, s)
            if msg: log.info(msg); continue
        except importer.ImportError_ as e:
            log.error("Modellimport abgelehnt: %s", e)
        except Exception as e:
            log.error("Modellimport fehlgeschlagen: %r", e)
        now = asyncio.get_running_loop().time()
        if now - last_hint > 300:
            shown = inst.problems[:2] + ([f"... und {len(inst.problems) - 2} weitere"] if len(inst.problems) > 2 else [])
            log.warning("%s Fehlt: %s", HOWTO, "; ".join(shown)); last_hint = now
        try: await asyncio.wait_for(stop.wait(), 5)
        except asyncio.TimeoutError: pass
    return False

UPGRADE_HINT = ("Das installierte Modellpaket enthaelt noch kein FP32-Hauptmodell - die App nutzt vorerst INT8, das oefter Woerter "
                "verschluckt. Neues Modellpaket wie beim ersten Import bereitstellen (DOCS.md, Abschnitt 3); es wird im laufenden Betrieb uebernommen.")

async def upgrade_models(s, engine, synth, stop):
    """Altes Modellpaket (nur INT8): neues Paket im laufenden Betrieb uebernehmen, dann Engine mit FP32-Hauptmodell neu starten."""
    log.warning(UPGRADE_HINT); state = {}; loop = asyncio.get_running_loop()
    while not stop.is_set():
        try:
            msg = await loop.run_in_executor(None, importer.try_upgrade, s, state)
            if msg:
                log.info("%s Starte die Engine mit FP32-Hauptmodell neu ...", msg)
                async with synth.lock: await engine.restart()
                await asyncio.wait_for(engine.ready.wait(), 150)
                await wyoming_server.warmup(synth, s); return
        except importer.ImportError_ as e:
            log.error("Neues Modellpaket abgelehnt: %s", e)
        except Exception as e:
            log.error("Uebernahme des neuen Modellpakets fehlgeschlagen: %r", e)
        try: await asyncio.wait_for(stop.wait(), 10)
        except asyncio.TimeoutError: pass

async def amain():
    try: s = cfg.load()
    except cfg.SettingsError as e:
        setup_logging("info"); log.error("Ungueltige Konfiguration: %s", e); return 2
    setup_logging(s.log_level)
    log.info("PocketTTS Local INT8 %s startet (Sprache %s, Standardstimme %s, Hauptmodell %s)", VERSION, s.language, s.default_voice, s.main_model.upper())
    stop = asyncio.Event(); loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT): loop.add_signal_handler(sig, stop.set)
    stub = asyncio.create_task(wyoming_server.run_stub(f"tcp://0.0.0.0:{WYOMING_PORT}"))
    await asyncio.sleep(0.5)
    for sig in (signal.SIGTERM, signal.SIGINT): loop.add_signal_handler(sig, stop.set)      # wyoming ersetzt die Handler (siehe unten)
    set_waiting(True)
    ok = await wait_for_models(s, stop)
    set_waiting(False); stub.cancel(); await asyncio.gather(stub, return_exceptions=True); await asyncio.sleep(0.3)
    if not ok: return 0
    added = importer.sync_custom_voices()
    if added: log.info("Eigene Stimmen uebernommen: %s", ", ".join(added))
    voices = importer.voices()
    if s.default_voice not in voices:
        log.warning("Standardstimme '%s' nicht gefunden - verwende '%s'.", s.default_voice, voices[0]); s = cfg.Settings(**{**s.__dict__, "default_voice": voices[0]})
    engine = Engine(s); engine.start()
    try: await asyncio.wait_for(engine.ready.wait(), 150)
    except asyncio.TimeoutError:
        log.error("PocketTTS-Engine wurde nicht bereit (siehe Meldungen oben)."); await engine.stop(); return 1
    synth, server, factory = await wyoming_server.serve(s, f"tcp://0.0.0.0:{WYOMING_PORT}", VERSION)
    synth.ready = engine.ready
    server_task = asyncio.create_task(server.run(factory))
    exit_code = [0]

    def server_done(t):                              # Server darf nie still sterben: App beenden, Supervisor startet neu
        if stop.is_set(): return
        exc = None if t.cancelled() else t.exception()
        log.error("Wyoming-Server wurde unerwartet beendet: %r - App wird beendet.", exc); exit_code[0] = 1; stop.set()
    server_task.add_done_callback(server_done)
    await asyncio.sleep(0.5)
    # wyoming.AsyncServer.run() ersetzt den SIGTERM-Handler durch einen eigenen: unseren danach wieder installieren
    for sig in (signal.SIGTERM, signal.SIGINT): loop.add_signal_handler(sig, stop.set)
    loop.run_in_executor(None, discovery.send, WYOMING_PORT)
    warm = asyncio.create_task(wyoming_server.warmup(synth, s)) if s.warmup else None
    upgrade = asyncio.create_task(upgrade_models(s, engine, synth, stop)) if s.main_model == "fp32" and not importer.has_fp32_main() else None
    log.info("Bereit: Wyoming-Port %d, %d Stimmen.", WYOMING_PORT, len(voices))
    await stop.wait()
    log.info("Beende ...")
    for t in (warm, upgrade, server_task):
        if t: t.cancel()
    await engine.stop(); return exit_code[0]

def main():
    sys.exit(asyncio.run(amain()))

if __name__ == "__main__":
    main()
