"""Wyoming-TTS-Server: reicht Audio aus der Inferenz sofort durch (echtes Streaming), mit deutscher Textnormalisierung."""
import asyncio, logging, os, re, time
import numpy as np
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize, SynthesizeChunk, SynthesizeStart, SynthesizeStop, SynthesizeStopped
from . import importer
from .engine import PORT as PT_PORT
from .german_norm import normalize
from .ttsclient import TtsError, stream_pcm

log = logging.getLogger("wyoming")
RATE = 24000
OUT_SAMPLES = 2048          # Samples je AudioChunk (~85 ms)
TRIM_THRESH = 0.01          # fuehrende Stille bis ca. -40 dBFS entfernen
PREROLL_MS = 30
GAP_MS = 180                # Pause zwischen Saetzen im Streaming-Eingabemodus
_ABBR = ["z. B.", "z.B.", "d. h.", "d.h.", "u. a.", "u.a.", "ca.", "Dr.", "Nr.", "bzw.", "evtl.", "ggf.", "usw.", "Prof.", "Hr.", "Fr.", "Std.", "Min.", "Sek."]

def split_sentences(text):
    t = text
    for a in _ABBR: t = t.replace(a, a.replace(".", "\u2024"))
    t = re.sub(r"(\d)\.(\s*\d)", "\\1\u2024\\2", t)
    return [p.replace("\u2024", ".").strip() for p in re.split(r"(?<=[.!?])\s+(?=\S)", t.strip()) if p.strip()]

def split_stream(buf):
    """Streaming-Eingabe: (vollstaendige Saetze, Rest). Der Rest bleibt unveraendert (inkl. Leerzeichen am Ende),
    damit Woerter ueber Chunk-Grenzen hinweg nicht zusammenfallen ("21 " + "Grad." -> "21 Grad.")."""
    t = buf
    for a in _ABBR: t = t.replace(a, a.replace(".", "\u2024"))
    t = re.sub(r"(\d)\.(\s*\d)", "\\1\u2024\\2", t)
    last = None
    for m in re.finditer(r"(?<=[.!?])\s+(?=\S)", t): last = m
    if last is None: return [], buf
    return split_sentences(buf[:last.start()]), buf[last.end():]

class ClientGone(Exception):
    """Der Wyoming-Client hat die Verbindung waehrend der Ausgabe beendet (kein Engine-Fehler)."""

class Synth:
    """Eine Synthese zur Zeit (der C++-Server hat einen Mutex); weitere Anfragen warten in der Schlange."""
    def __init__(self, settings):
        self.s = settings; self.lock = asyncio.Lock(); self.default_voice = settings.default_voice; self.requests = 0; self.errors = 0
        self.ready = asyncio.Event(); self.ready.set()      # main.py verbindet das mit dem Bereit-Status der Engine
        self.ready_timeout = 10.0

    def voice_ok(self, name):
        return name if name and name in importer.voices() else self.default_voice

class Handler(AsyncEventHandler):
    def __init__(self, info, synth, *a, **kw):
        super().__init__(*a, **kw); self.info_event = info.event(); self.synth = synth; self.s = synth.s
        self.buf = ""; self.voice = synth.default_voice; self.streaming_in = False; self.started = False; self.error = None

    async def _emit(self, x):
        try:
            if not self.started:
                await self.write_event(AudioStart(rate=RATE, width=2, channels=1).event()); self.started = True
            pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes(); step = OUT_SAMPLES * 2
            for i in range(0, len(pcm), step):
                await self.write_event(AudioChunk(audio=pcm[i:i + step], rate=RATE, width=2, channels=1).event())
        except (ConnectionError, OSError, TypeError, RuntimeError) as e:
            raise ClientGone(type(e).__name__) from e

    async def _speak(self, text, gap_first):
        if not text: return
        if self.s.normalize_text: text = normalize(text)
        s = self.s; t0 = time.perf_counter(); first_out = None; total = 0; carry = b""; lead_done = False
        pend = []; pend_n = 0; released = self.started and s.streaming
        prebuf = s.prebuffer_ms if s.streaming else 10**9
        async with self.synth.lock:
            self.synth.requests += 1
            try:                                              # Engine gerade im Neustart? Kurz warten statt sofort scheitern
                await asyncio.wait_for(self.synth.ready.wait(), self.synth.ready_timeout)
            except asyncio.TimeoutError:
                self.synth.errors += 1; self.error = "Die Sprach-Engine ist nicht bereit."; log.error(self.error); return
            gen = stream_pcm("127.0.0.1", PT_PORT, text, self.voice + ".wav")
            try:
                async for raw in gen:
                    carry += raw; k = len(carry) // 4 * 4
                    if not k: continue
                    x = np.frombuffer(carry[:k], dtype="<f4"); carry = carry[k:]
                    if not lead_done:
                        hit = np.nonzero(np.abs(x) > TRIM_THRESH)[0]
                        if not hit.size: continue
                        x = x[max(0, hit[0] - RATE * PREROLL_MS // 1000):]; lead_done = True
                        if gap_first and self.started: x = np.concatenate([np.zeros(RATE * GAP_MS // 1000, np.float32), x])
                    if not released:
                        pend.append(x); pend_n += len(x)
                        if pend_n * 1000 < prebuf * RATE: continue
                        x = np.concatenate(pend); pend = []; released = True
                    await self._emit(x); total += len(x)
                    if first_out is None: first_out = time.perf_counter() - t0
                if pend:
                    x = np.concatenate(pend); await self._emit(x); total += len(x)
                    if first_out is None: first_out = time.perf_counter() - t0
            except (TtsError, OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as e:
                self.synth.errors += 1; self.error = f"Synthese fehlgeschlagen ({type(e).__name__})"; log.error("Synthese fehlgeschlagen (%s): %r", type(e).__name__, e)
            finally:
                await gen.aclose()
        if total == 0 and not self.error:                       # kein einziges Sample: defekte/fehlende Stimmdatei oder Engine-Problem
            self.synth.errors += 1; self.error = f"Keine Audiodaten erzeugt (Stimme '{self.voice}')"
            log.error("%s - Stimmdatei %s/%s.wav pruefen (defekt oder unlesbar?).", self.error, importer.VOICES, self.voice)
        log.info("Stimme %s: %d Zeichen -> %.1fs Audio, erster Chunk nach %.2fs, gesamt %.2fs", self.voice, len(text), total / RATE, first_out if first_out is not None else -1, time.perf_counter() - t0)

    async def _finish(self):
        if self.error:                                         # Fehler melden statt den Client bis zum Timeout warten zu lassen
            err, self.error = self.error, None; self.started = False
            await self.write_event(Error(text=err, code="synthesis-failed").event()); return
        if self.started: await self.write_event(AudioStop().event())
        self.started = False

    async def handle_event(self, event: Event) -> bool:
        try:
            return await self._handle(event)
        except (ClientGone, ConnectionError, OSError, TypeError, RuntimeError, asyncio.IncompleteReadError) as e:
            # Client hat mitten in der Ausgabe getrennt (z. B. Satellit unterbrochen) -> Synthese wurde bereits abgebrochen
            log.info("Client-Verbindung beendet (%s) - Synthese abgebrochen.", type(e).__name__); return False

    async def _handle(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.info_event); return True
        if Synthesize.is_type(event.type):
            if self.streaming_in: return True
            e = Synthesize.from_event(event); self.voice = self.synth.voice_ok(e.voice.name if e.voice else None)
            await self._speak(e.text.strip(), gap_first=False); await self._finish(); return True
        if SynthesizeStart.is_type(event.type):
            e = SynthesizeStart.from_event(event); self.voice = self.synth.voice_ok(e.voice.name if e.voice else None); self.streaming_in = True; self.buf = ""; return True
        if SynthesizeChunk.is_type(event.type):
            self.buf += SynthesizeChunk.from_event(event).text
            done, self.buf = split_stream(self.buf)
            for sent in done: await self._speak(sent, gap_first=True)
            return True
        if SynthesizeStop.is_type(event.type):
            for sent in split_sentences(self.buf): await self._speak(sent, gap_first=True)
            self.buf = ""; await self._finish(); await self.write_event(SynthesizeStopped().event()); self.streaming_in = False; return True
        return True

def build_info(settings, version):
    attr = Attribution(name="Kyutai Pocket TTS (lokal, INT8)", url="https://huggingface.co/kyutai/pocket-tts")
    voices = [TtsVoice(name=v, description=f"PocketTTS {v}" + (" (Standard)" if v == settings.default_voice else ""), attribution=attr, installed=True, version=None, languages=["de"]) for v in importer.voices()]
    return Info(tts=[TtsProgram(name="pockettts-local-int8", description="PocketTTS German INT8 (CPU, offline, Streaming)", attribution=attr, installed=True,
                                version=version, voices=voices, supports_synthesize_streaming=True)])

async def warmup(synth, settings):
    """Modell und Stimm-/KV-Caches vorwaermen (Standardstimme zuerst)."""
    order = [synth.default_voice] + ([v for v in importer.voices() if v != synth.default_voice] if settings.preload_voices else [])
    for v in order:
        t = time.perf_counter()
        async with synth.lock:
            try:
                async for _ in stream_pcm("127.0.0.1", PT_PORT, "Hallo.", v + ".wav"): pass
                log.info("Warmup %s: %.1fs", v, time.perf_counter() - t)
            except Exception as e:
                log.warning("Warmup %s fehlgeschlagen (defekte Stimmdatei?): %r", v, e)

class _StubHandler(AsyncEventHandler):
    """Platzhalter, solange noch keine Modelle importiert sind: Port offen, Describe wird mit leerer Dienstliste beantwortet."""
    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type): await self.write_event(Info(tts=[]).event())
        return True

async def run_stub(uri):
    await AsyncServer.from_uri(uri).run(_StubHandler)

async def serve(settings, uri, version):
    synth = Synth(settings)
    info = build_info(settings, version)
    log.info("Wyoming-Server auf %s, Stimmen: %s", uri, ",".join(v.name for v in info.tts[0].voices))
    server = AsyncServer.from_uri(uri)
    return synth, server, (lambda *a, **k: Handler(info, synth, *a, **k))
