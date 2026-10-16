"""Klangaufbereitung fuer das gestreamte Audio: Klangkorrektur (linearphasiger FIR nach Zielkurve), Verstaerkung, weicher Limiter.
PocketTTS klingt dumpf: gemessen gut 10 dB zu viel Droehnen unter 100 Hz und ca. 8 dB zu wenig Praesenz bei 1,6-3 kHz gegenueber
klaren Sprachausgaben (Supertonic, Piper); dazu leise (ca. -26 dBFS RMS). Die Profile gleichen das Langzeitspektrum daran an
("klar" = im Hoertest bevorzugt). Zustandsbehaftet je Satz, damit Chunk-Grenzen nahtlos bleiben; Verzoegerung ca. 5 ms."""
import numpy as np

RATE = 24000
TAPS = 255
CURVE_HZ = [60, 90, 130, 200, 300, 450, 700, 1000, 1400, 1800, 2300, 3000, 4000, 5500, 7500, 11000]
PROFILES = {   # dB je Stuetzstelle (dazwischen linear ueber log f); Pegelaenderung auf typischer Ausgabe < 1 dB
    "klar":  [-12.0, -10.4, -4.5, 0.2, -0.2, 0.2, 1.0, 1.3, 3.7, 8.5, 13.3, 15.0, 15.0, 11.5, 10.9, 15.0],
    "weich": [-12.0, -10.4, -4.5, 0.2, -0.2, 0.2, 1.0, 1.3, 3.7, 7.4, 10.8, 12.0, 12.0, 8.5, 7.9, 12.0],
    "aus":   None,
}

def curve_fir(gains_db, freqs=CURVE_HZ, taps=TAPS, rate=RATE):
    n = 8192; f = np.fft.rfftfreq(n, 1 / rate)
    g = np.interp(np.log(np.maximum(f, 1)), np.log(freqs), gains_db)
    h = np.fft.irfft(10 ** (g / 20), n)
    return (np.roll(h, taps // 2)[:taps] * np.hanning(taps + 2)[1:-1]).astype(np.float32)

_FIR = {}

class Enhancer:
    def __init__(self, gain_db=0, profile="aus", limit=0.85):
        self.gain = float(10 ** (gain_db / 20)); self.limit = limit
        if PROFILES.get(profile) is not None and profile not in _FIR: _FIR[profile] = curve_fir(PROFILES[profile])
        self.h = _FIR.get(profile) if PROFILES.get(profile) is not None else None
        self.tail = np.zeros(TAPS - 1, np.float32)
        self.active = bool(gain_db) or self.h is not None

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
