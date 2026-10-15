"""Minimaler asynchroner HTTP-Client fuer POST /tts (chunked float32-PCM, 24 kHz) ueber Loopback."""
import asyncio, json

class TtsError(Exception):
    pass

async def stream_pcm(host, port, text, voice, timeout=120):
    """Async-Generator: liefert Roh-Bytes (float32 LE) sobald sie ankommen. Schliessen des Generators bricht die Synthese ab."""
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), 5)
    try:
        body = json.dumps({"text": text, "voice": voice}, ensure_ascii=False).encode("utf-8")
        writer.write(b"POST /tts HTTP/1.1\r\nHost: %b\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (host.encode(), len(body)) + body)
        await writer.drain()
        status = await asyncio.wait_for(reader.readline(), timeout)
        parts = status.split()
        if len(parts) < 2 or parts[1] != b"200": raise TtsError(f"PocketTTS-Server antwortete mit {status.strip()!r}")
        chunked = False; length = None
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout)
            if line in (b"\r\n", b"\n", b""): break
            k, _, v = line.decode("latin-1").partition(":"); k = k.strip().lower(); v = v.strip().lower()
            if k == "transfer-encoding" and "chunked" in v: chunked = True
            if k == "content-length": length = int(v)
        if chunked:
            while True:
                size_line = await asyncio.wait_for(reader.readline(), timeout)
                size = int(size_line.split(b";")[0].strip() or b"0", 16)
                if size == 0: break
                data = await asyncio.wait_for(reader.readexactly(size), timeout); await reader.readexactly(2)
                yield data
        else:
            remaining = length
            while remaining is None or remaining > 0:
                data = await asyncio.wait_for(reader.read(65536 if remaining is None else min(65536, remaining)), timeout)
                if not data: break
                if remaining is not None: remaining -= len(data)
                yield data
    finally:
        writer.close()
