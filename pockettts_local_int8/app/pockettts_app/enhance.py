"""Klangaufbereitung fuer das gestreamte Audio: Hoehenanhebung (linearphasiger FIR-Shelf), Verstaerkung, weicher Limiter.
PocketTTS klingt dumpf (gemessen: ca. 0,5 % der Energie ueber 3 kHz, Referenzstimmen 2-3 %) und leise (ca. -26 dBFS RMS).
Zustandsbehaftet je Satz, damit Chunk-Grenzen nahtlos bleiben; Verzoegerung durch den Filter ca. 1,3 ms."""
import numpy as np

RATE = 24000
TAPS = 63

def shelf_fir(treble_db, f1=1500.0, f2=4000.0, taps=TAPS, rate=RATE):
    """FIR mit 0 dB unter f1 und treble_db ueber f2 (dazwischen linear in dB ueber log f)."""
    n = 4096; f = np.fft.rfftfreq(n, 1 / rate)
    g = np.clip(np.log(np.maximum(f, 1) / f1) / np.log(f2 / f1), 0, 1) * treble_db
    h = np.fft.irfft(10 ** (g / 20), n)
    return (np.roll(h, taps // 2)[:taps] * np.hanning(taps + 2)[1:-1]).astype(np.float32)

class Enhancer:
    def __init__(self, gain_db=0, treble_db=0, limit=0.85):
        self.gain = float(10 ** (gain_db / 20)); self.limit = limit
        self.h = shelf_fir(treble_db) if treble_db else None
        self.tail = np.zeros(TAPS - 1, np.float32)
        self.active = bool(gain_db or treble_db)

    def process(self, x):
        x = np.asarray(x, np.float32)
        if not self.active or not x.size: return x
        if self.h is not None:
            buf = np.concatenate([self.tail, x]); self.tail = buf[-(TAPS - 1):]
            x = np.convolve(buf, self.h, mode="valid").astype(np.float32)
        y = x * self.gain; t = self.limit; a = np.abs(y); over = a > t
        if over.any(): y[over] = np.sign(y[over]) * (t + (1 - t) * np.tanh((a[over] - t) / (1 - t)))
        return y

    def flush(self):
        """Rest des Filters (halbe Filterlaenge) am Satzende."""
        return self.process(np.zeros((TAPS - 1) // 2, np.float32)) if self.h is not None else np.zeros(0, np.float32)
