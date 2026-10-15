"""Docker-Healthcheck: Wyoming Describe/Info-Rundlauf mit mindestens einer Stimme (nicht nur ein offener Port)."""
import asyncio, os, sys
from wyoming.client import AsyncClient
from wyoming.info import Describe, Info

async def check(uri, timeout=6):
    async with AsyncClient.from_uri(uri) as c:
        await c.write_event(Describe().event())
        while True:
            ev = await asyncio.wait_for(c.read_event(), timeout)
            if ev is None: return False
            if Info.is_type(ev.type):
                info = Info.from_event(ev); return any(p.voices for p in info.tts)

if __name__ == "__main__":
    uri = os.environ.get("HEALTH_URI", "tcp://127.0.0.1:10302")
    try: ok = asyncio.run(asyncio.wait_for(check(uri), 8))
    except Exception: ok = False
    sys.exit(0 if ok else 1)
