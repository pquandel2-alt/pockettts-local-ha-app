"""PocketTTS.cpp-Server als ueberwachter Kindprozess (Loopback, Neustart mit Backoff, sauberes Beenden)."""
import asyncio, logging, os, signal
from . import importer

log = logging.getLogger("engine")
BIN = os.environ.get("PT_BIN", "/opt/pt/pocket-tts")
PORT = int(os.environ.get("PT_PORT", "8092"))

def build_args(s):
    return [BIN, "--server", "--port", str(PORT), "--models-dir", importer.MODELS, "--tokenizer", f"{importer.MODELS}/tokenizer.model",
            "--voices-dir", importer.VOICES, "--precision", "int8", "--threads", str(s.threads), "--lead-in-ms", str(s.lead_in_ms),
            "--first-chunk", str(s.first_chunk), "--max-chunk", str(s.max_chunk), "--temperature", str(s.temperature)]

def main_precision(s):
    """Hauptmodell in FP32, wenn gewuenscht und vorhanden (sonst INT8 wie bis 1.0.1)."""
    return "fp32" if s.main_model == "fp32" and importer.has_fp32_main() else "int8"

def build_env(s):
    env = {k: v for k, v in os.environ.items() if not k.upper().endswith(("TOKEN", "SECRET", "PASSWORD"))}   # keine Geheimnisse an das Kind
    env["PTT_BIND_ADDR"] = "127.0.0.1"
    env["PTT_ORT_ALLOW_SPINNING"] = "1" if s.ort_spinning else "0"
    env["PTT_MAIN_PRECISION"] = main_precision(s)
    env["ORT_DISABLE_TELEMETRY"] = "1"
    return env

class Engine:
    def __init__(self, settings):
        self.s = settings; self.proc = None; self.task = None; self.stopping = False; self.restarts = 0; self.ready = asyncio.Event(); self.restarting = False

    _KEEP = ("loading", "loaded", "listening", "shutting", "error", "fail", "warn", "invalid", "cannot", "missing", "exception")

    async def _pump(self, stream, name):
        debug = self.s.log_level == "debug"
        while True:
            line = await stream.readline()
            if not line: return
            t = line.decode("utf-8", "replace").rstrip()
            if not t: continue
            if debug: log.debug("[server] %s", t); continue
            if t.lstrip().startswith(("Generating:", "PTT_DBG")): continue            # gesprochener Text gehoert nicht ins Info-Log
            if any(k in t.lower() for k in self._KEEP): log.info("[server] %s", t.strip()[:300])

    async def _run(self):
        backoff = 1
        while not self.stopping:
            self.ready.clear()
            log.info("Starte PocketTTS-Engine (Hauptmodell %s, threads=%d, first_chunk=%d, max_chunk=%d, spinning=%s)",
                     main_precision(self.s).upper(), self.s.threads, self.s.first_chunk, self.s.max_chunk, self.s.ort_spinning)
            self.proc = await asyncio.create_subprocess_exec(*build_args(self.s), env=build_env(self.s), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            pumps = asyncio.gather(self._pump(self.proc.stdout, "out"))
            started = asyncio.get_running_loop().time()
            waiter = asyncio.create_task(self._wait_healthy())
            rc = await self.proc.wait(); self.ready.clear(); waiter.cancel(); await pumps
            if self.stopping: return
            if self.restarting:
                self.restarting = False; backoff = 1; continue
            ran = asyncio.get_running_loop().time() - started
            backoff = 1 if ran > 60 else min(backoff * 2, 30)
            self.restarts += 1
            log.error("PocketTTS-Engine beendet (Code %s) nach %.0fs - Neustart in %ds (Neustart Nr. %d)", rc, ran, backoff, self.restarts)
            await asyncio.sleep(backoff)

    async def _wait_healthy(self):
        for _ in range(240):
            if await http_health(): self.ready.set(); log.info("PocketTTS-Engine ist bereit."); return
            await asyncio.sleep(0.5)
        log.error("PocketTTS-Engine wurde nicht innerhalb von 120 s bereit.")

    def start(self): self.task = asyncio.create_task(self._run())

    async def restart(self):
        """Geplanter Neustart (z. B. nach Import des neuen Modellpakets); kein Fehler, kein Backoff."""
        if self.proc and self.proc.returncode is None:
            self.restarting = True; self.proc.send_signal(signal.SIGTERM)
            try: await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError: self.proc.kill()

    async def stop(self):
        self.stopping = True
        if self.proc and self.proc.returncode is None:
            self.proc.send_signal(signal.SIGTERM)
            try: await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError: self.proc.kill(); await self.proc.wait()
        if self.task: self.task.cancel()

async def http_health(host="127.0.0.1", port=PORT, timeout=2.0):
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        w.write(f"GET /health HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
        await w.drain(); data = await asyncio.wait_for(r.read(256), timeout); w.close()
        return data.startswith(b"HTTP/1.1 200") or data.startswith(b"HTTP/1.0 200")
    except (OSError, asyncio.TimeoutError):
        return False
