"""Einstiegspunkt der App: Optionen -> Modellimport -> Engine -> Wyoming-Server -> Discovery/Warmup; sauberes Beenden bei SIGTERM."""
import asyncio, logging, os, signal, sys
from . import discovery, importer, settings as cfg, wyoming_server
from .engine import Engine

log = logging.getLogger("app")
VERSION = os.environ.get("APP_VERSION", "dev")
WYOMING_PORT = int(os.environ.get("WYOMING_PORT", "10302"))

HOWTO = ("Es sind noch keine Modelldateien vorhanden. Lege das Modellpaket 'pockettts-model-pack.tar.gz' in den App-Konfigurationsordner "
         "(Samba-Freigabe 'addon_configs' -> Ordner dieser App; innerhalb der App unter /config) oder nach /share/pockettts/, "
         "oder trage unter 'Konfiguration' einen LAN-Link (import_url) ein. Die App importiert es automatisch, kein Neustart noetig. Siehe DOCS.md.")

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
            log.error("%s Probleme: %s", HOWTO, "; ".join(inst.problems)); last_hint = now
        try: await asyncio.wait_for(stop.wait(), 15)
        except asyncio.TimeoutError: pass
    return False

async def amain():
    try: s = cfg.load()
    except cfg.SettingsError as e:
        setup_logging("info"); log.error("Ungueltige Konfiguration: %s", e); return 2
    setup_logging(s.log_level)
    log.info("PocketTTS Local INT8 %s startet (Sprache %s, Standardstimme %s)", VERSION, s.language, s.default_voice)
    stop = asyncio.Event(); loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT): loop.add_signal_handler(sig, stop.set)
    if not await wait_for_models(s, stop): return 0
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
    log.info("Bereit: Wyoming-Port %d, %d Stimmen.", WYOMING_PORT, len(voices))
    await stop.wait()
    log.info("Beende ...")
    for t in (warm, server_task):
        if t: t.cancel()
    await engine.stop(); return exit_code[0]

def main():
    sys.exit(asyncio.run(amain()))

if __name__ == "__main__":
    main()
