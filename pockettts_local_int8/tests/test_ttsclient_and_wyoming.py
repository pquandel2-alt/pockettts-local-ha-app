import asyncio, os, tempfile, unittest
import numpy as np

# Umgebung vor dem Import der App-Module festlegen
_d = tempfile.mkdtemp(); os.makedirs(f"{_d}/voices_de")
for v in ("juergen", "paul"): open(f"{_d}/voices_de/{v}.wav", "wb").write(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 3000)
os.environ.update(DATA_DIR=_d, PT_PORT="18092")

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncClient
from wyoming.error import Error
from wyoming.info import Describe, Info
from wyoming.tts import Synthesize, SynthesizeChunk, SynthesizeStart, SynthesizeStop, SynthesizeStopped, SynthesizeVoice
from pockettts_app import importer, settings as cfg, wyoming_server
from pockettts_app.ttsclient import TtsError, stream_pcm

RATE = 24000
def fake_audio(silence_s=0.4, tone_s=0.6):
    t = np.arange(int(tone_s * RATE)) / RATE
    return np.concatenate([np.zeros(int(silence_s * RATE), np.float32), (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)])

class FakeEngine:
    """Simuliert PocketTTS.cpp: chunked float32-PCM; fuehrende Stille; Satzzahl = Anzahl Anfragen."""
    def __init__(self): self.requests = []; self.aborted = 0; self.silent = False
    async def handle(self, r, w):
        head = await r.readuntil(b"\r\n\r\n"); n = int([l for l in head.split(b"\r\n") if l.lower().startswith(b"content-length")][0].split(b":")[1])
        import json; body = json.loads(await r.readexactly(n)); self.requests.append(body)
        if body["text"] == "FEHLER":
            w.write(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n"); await w.drain(); w.close(); return
        w.write(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Type: audio/pcm\r\n\r\n")
        if self.silent: w.write(b"0\r\n\r\n"); await w.drain(); w.close(); return      # 200 OK ohne Audio (z. B. defekte Stimme)
        pcm = fake_audio().tobytes()
        try:
            for i in range(0, len(pcm), 7680):
                c = pcm[i:i + 7680]; w.write(b"%x\r\n" % len(c) + c + b"\r\n"); await w.drain(); await asyncio.sleep(0.01)
            w.write(b"0\r\n\r\n"); await w.drain()
        except (ConnectionError, OSError): self.aborted += 1
        w.close()

class Flow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        importer.VOICES = f"{_d}/voices_de"     # unabhaengig von anderen Tests (Importer-Tests laden das Modul neu)
        self.fake = FakeEngine(); self.srv = await asyncio.start_server(self.fake.handle, "127.0.0.1", 18092)
        self.s = cfg.Settings(prebuffer_ms=150)
        self.synth, server, factory = await wyoming_server.serve(self.s, "tcp://127.0.0.1:0", "test")
        self.info = wyoming_server.build_info(self.s, "test")
        # eigenen Port waehlen
        self.port = 18302; self.wy = asyncio.create_task(wyoming_server.AsyncServer.from_uri(f"tcp://127.0.0.1:{self.port}").run(factory)); await asyncio.sleep(0.2)

    async def asyncTearDown(self):
        self.wy.cancel(); self.srv.close(); await self.srv.wait_closed()

    async def collect(self, c, until="audio-stop"):
        ev_types, pcm, first = [], b"", None; t0 = asyncio.get_running_loop().time()
        while True:
            ev = await asyncio.wait_for(c.read_event(), 10); ev_types.append(ev.type)
            if AudioChunk.is_type(ev.type):
                if first is None: first = asyncio.get_running_loop().time() - t0
                pcm += AudioChunk.from_event(ev).audio
            if ev.type == until: return ev_types, pcm, first

    async def test_chunked_client(self):
        got = b"".join([c async for c in stream_pcm("127.0.0.1", 18092, "Hallo", "juergen.wav")])
        self.assertEqual(len(got), len(fake_audio().tobytes()))

    async def test_client_error_status(self):
        with self.assertRaises(TtsError):
            async for _ in stream_pcm("127.0.0.1", 18092, "FEHLER", "juergen.wav"): pass

    async def test_describe_lists_voices_and_streaming(self):
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Describe().event()); ev = await c.read_event()
        info = Info.from_event(ev); self.assertEqual(sorted(v.name for v in info.tts[0].voices), ["juergen", "paul"]); self.assertTrue(info.tts[0].supports_synthesize_streaming)
        self.assertEqual(info.tts[0].voices[0].languages, ["de"])

    async def test_synthesize_trims_silence_and_streams(self):
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Synthesize(text="Es ist 18 Uhr 35.", voice=SynthesizeVoice(name="paul")).event()); types, pcm, first = await self.collect(c)
        self.assertEqual(types[0], "audio-start"); self.assertEqual(types[-1], "audio-stop")
        x = np.frombuffer(pcm, "<i2") / 32768.0
        self.assertLess(len(x) / RATE, 0.75)                      # 0,4 s Stille abgeschnitten (nur ca. 150 ms Vorlauf bleiben)
        self.assertGreater(np.abs(x[: RATE // 20]).max(), 0.05)   # der erste Chunk ist hoerbar, keine Stille
        self.assertEqual(self.fake.requests[-1]["voice"], "paul.wav"); self.assertEqual(self.fake.requests[-1]["text"], "Es ist achtzehn Uhr fünfunddreißig.")

    async def _peak(self, settings):
        _, _, factory = await wyoming_server.serve(settings, "tcp://127.0.0.1:0", "test")
        task = asyncio.create_task(wyoming_server.AsyncServer.from_uri("tcp://127.0.0.1:18303").run(factory)); await asyncio.sleep(0.2)
        try:
            async with AsyncClient.from_uri("tcp://127.0.0.1:18303") as c:
                await c.write_event(Synthesize(text="Hallo.").event()); _, pcm, _ = await self.collect(c)
        finally: task.cancel()
        return np.abs(np.frombuffer(pcm, "<i2") / 32768.0).max(), len(pcm) // 2

    async def test_volume_boost_and_limiter(self):
        off, n_off = await self._peak(cfg.Settings(prebuffer_ms=150, volume_boost_db=0, sound_profile="aus"))
        on, n_on = await self._peak(cfg.Settings(prebuffer_ms=150, volume_boost_db=8, sound_profile="aus"))
        hot, _ = await self._peak(cfg.Settings(prebuffer_ms=150, volume_boost_db=20, sound_profile="klar"))
        self.assertAlmostEqual(off, 0.3, delta=0.01); self.assertAlmostEqual(on / off, 10 ** (8 / 20), delta=0.05); self.assertEqual(n_on, n_off)
        self.assertLess(hot, 1.0)                                  # Limiter: keine harte Uebersteuerung

    async def test_unknown_voice_falls_back_to_default(self):
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Synthesize(text="Hallo.", voice=SynthesizeVoice(name="gibtsnicht")).event()); await self.collect(c)
        self.assertEqual(self.fake.requests[-1]["voice"], "juergen.wav")

    async def test_streaming_input_events(self):
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(SynthesizeStart(voice=SynthesizeVoice(name="juergen")).event())
            for part in ("Die Waschmaschine ", "ist fertig. ", "Es sind 21 ", "Grad."): await c.write_event(SynthesizeChunk(text=part).event())
            await c.write_event(SynthesizeStop().event()); types, pcm, _ = await self.collect(c, until="synthesize-stopped")
        self.assertIn("audio-start", types); self.assertEqual(types[-1], "synthesize-stopped"); self.assertEqual(types[-2], "audio-stop")
        self.assertEqual([r["text"] for r in self.fake.requests[-2:]], ["Die Waschmaschine ist fertig.", "Es sind einundzwanzig Grad."])

    async def test_engine_error_is_reported_as_error_event_and_does_not_hang(self):
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Synthesize(text="FEHLER").event()); ev = await asyncio.wait_for(c.read_event(), 5)
            self.assertEqual(ev.type, "error"); self.assertEqual(Error.from_event(ev).code, "synthesis-failed")
            await c.write_event(Describe().event()); ev = await asyncio.wait_for(c.read_event(), 5); self.assertEqual(ev.type, "info")   # Verbindung bleibt nutzbar
        self.assertEqual(self.synth.errors, 1)

    async def test_silent_engine_result_is_reported_as_error(self):
        self.fake.silent = True
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Synthesize(text="Hallo.", voice=SynthesizeVoice(name="paul")).event()); ev = await asyncio.wait_for(c.read_event(), 5)
        self.assertEqual(ev.type, "error"); self.assertIn("paul", Error.from_event(ev).text)

    async def test_request_waits_for_engine_restart(self):
        self.synth.ready.clear(); self.synth.ready_timeout = 5
        async def later(): await asyncio.sleep(1.0); self.synth.ready.set()
        asyncio.create_task(later())
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Synthesize(text="Hallo.").event()); types, pcm, first = await self.collect(c)
        self.assertEqual(types[-1], "audio-stop"); self.assertGreater(first, 0.9); self.assertGreater(len(pcm), 0)

    async def test_not_ready_in_time_returns_error(self):
        self.synth.ready.clear(); self.synth.ready_timeout = 0.5
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c:
            await c.write_event(Synthesize(text="Hallo.").event()); ev = await asyncio.wait_for(c.read_event(), 5)
        self.assertEqual(ev.type, "error")

    async def test_non_streaming_mode_sends_one_block_after_completion(self):
        self.s2 = cfg.Settings(streaming=False); synth, _, factory = await wyoming_server.serve(self.s2, "tcp://127.0.0.1:0", "t")
        t = asyncio.create_task(wyoming_server.AsyncServer.from_uri("tcp://127.0.0.1:18303").run(factory)); await asyncio.sleep(0.2)
        try:
            async with AsyncClient.from_uri("tcp://127.0.0.1:18303") as c:
                await c.write_event(Synthesize(text="Hallo.").event()); types, pcm, first = await self.collect(c)
            self.assertEqual(types[0], "audio-start"); self.assertGreater(len(pcm), 0)
        finally: t.cancel()

    async def test_client_disconnect_aborts_engine_request_and_service_stays_usable(self):
        c = AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}"); await c.connect()
        await c.write_event(Synthesize(text="Die Temperatur beträgt 12,5 Grad.", voice=SynthesizeVoice(name="juergen")).event())
        while True:
            ev = await asyncio.wait_for(c.read_event(), 5)
            if AudioChunk.is_type(ev.type): break
        await c.disconnect()                                     # Abbruch mitten in der Ausgabe
        for _ in range(50):
            if self.fake.aborted: break
            await asyncio.sleep(0.1)
        self.assertGreaterEqual(self.fake.aborted, 1)            # Engine-Anfrage wurde beendet
        async with AsyncClient.from_uri(f"tcp://127.0.0.1:{self.port}") as c2:    # Dienst funktioniert weiter (Lock frei)
            await c2.write_event(Synthesize(text="Hallo.").event()); types, pcm, _ = await self.collect(c2)
        self.assertEqual(types[-1], "audio-stop"); self.assertGreater(len(pcm), 0)

    def test_split_stream_keeps_whitespace_at_chunk_boundaries(self):
        self.assertEqual(wyoming_server.split_stream("Die Waschmaschine ist fertig. Es sind 21 "), (["Die Waschmaschine ist fertig."], "Es sind 21 "))
        self.assertEqual(wyoming_server.split_stream("Noch kein Satzende"), ([], "Noch kein Satzende"))
        self.assertEqual(wyoming_server.split_stream("Das ist z. B. gut"), ([], "Das ist z. B. gut"))
        self.assertEqual(wyoming_server.split_stream("A. B! C? Rest "), (["A.", "B!", "C?"], "Rest "))
        self.assertEqual(wyoming_server.split_stream("Satz eins. "), ([], "Satz eins. "))

    def test_split_handles_quotes_semicolons_and_dates(self):
        t = "Ich habe 2 Termine gefunden: \u201eFriseur\u201c am 18.10. um 09:00 Uhr; \u201eTeverner Heide\u201c am 18.10. um 14:00 Uhr."
        want = ["Ich habe 2 Termine gefunden.", "Friseur am 18.10. um 09:00 Uhr.", "Teverner Heide am 18.10. um 14:00 Uhr."]
        self.assertEqual(wyoming_server.split_sentences(t), want)
        self.assertEqual(wyoming_server.split_stream(t + " Weiter "), (want, "Weiter "))
        self.assertEqual(wyoming_server.split_sentences("Die Haust\u00fcr ist zu; die Garage ist offen."), ["Die Haust\u00fcr ist zu.", "Die Garage ist offen."])
        self.assertEqual(wyoming_server.split_sentences("Es ist 18:35 Uhr."), ["Es ist 18:35 Uhr."])
        self.assertEqual(wyoming_server.split_stream("Termin am 18.10. um "), ([], "Termin am 18.10. um "))

    def test_split_sentences_protects_abbreviations(self):
        self.assertEqual(wyoming_server.split_sentences("Das ist z. B. gut. Nr. 5 ist 12. Aber ja!"), ["Das ist z. B. gut.", "Nr. 5 ist 12.", "Aber ja!"])
        self.assertEqual(wyoming_server.split_sentences("Es sind 12.5 Grad. Wirklich?"), ["Es sind 12.5 Grad.", "Wirklich?"])

if __name__ == "__main__": unittest.main()

class Waiting(unittest.IsolatedAsyncioTestCase):
    async def test_stub_answers_describe_with_empty_service_list(self):
        t = asyncio.create_task(wyoming_server.run_stub("tcp://127.0.0.1:18310")); await asyncio.sleep(0.3)
        try:
            async with AsyncClient.from_uri("tcp://127.0.0.1:18310") as c:
                await c.write_event(Describe().event()); ev = await asyncio.wait_for(c.read_event(), 5)
            self.assertEqual(Info.from_event(ev).tts, [])
        finally: t.cancel()

    def test_healthcheck_is_healthy_while_waiting_for_models(self):
        import subprocess, sys, tempfile
        flag = tempfile.NamedTemporaryFile(delete=False).name
        env = {**os.environ, "WAITING_FLAG": flag, "HEALTH_URI": "tcp://127.0.0.1:1"}
        self.assertEqual(subprocess.run([sys.executable, "-m", "pockettts_app.healthcheck"], env=env, cwd="/opt/app" if os.path.isdir("/opt/app") else None).returncode, 0)
        os.remove(flag)
        self.assertEqual(subprocess.run([sys.executable, "-m", "pockettts_app.healthcheck"], env=env, cwd="/opt/app" if os.path.isdir("/opt/app") else None).returncode, 1)   # kein Flag, kein Server: unhealthy
