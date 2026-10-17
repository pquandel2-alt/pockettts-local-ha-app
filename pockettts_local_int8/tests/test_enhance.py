import unittest
import numpy as np
from pockettts_app.enhance import Enhancer, Leveler, curve_fir, PROFILES, RATE, TAPS

class Enhance(unittest.TestCase):
    def test_off_is_identity(self):
        x = np.random.default_rng(1).normal(0, .1, 5000).astype(np.float32); e = Enhancer(0, "aus")
        np.testing.assert_array_equal(e.process(x), x); self.assertEqual(e.flush().size, 0)
    def test_klar_profile_response(self):
        f = np.fft.rfftfreq(16384, 1 / RATE); H = 20 * np.log10(np.abs(np.fft.rfft(curve_fir(PROFILES["klar"]), 16384)))
        at = lambda fr: H[np.argmin(abs(f - fr))]
        self.assertLess(at(70), -6)                                   # Droehnen deutlich abgesenkt
        self.assertAlmostEqual(at(300), 0, delta=1.0); self.assertAlmostEqual(at(600), 0.5, delta=1.0)
        self.assertGreater(at(2500), 10); self.assertGreater(at(3500), 12)   # Praesenz angehoben
    def test_weich_is_gentler_than_klar(self):
        f = np.fft.rfftfreq(8192, 1 / RATE); i = np.argmin(abs(f - 3000))
        k, w = (20 * np.log10(np.abs(np.fft.rfft(curve_fir(PROFILES[p]), 8192)))[i] for p in ("klar", "weich")); self.assertGreater(k, w + 2)
    def test_streaming_equals_block(self):
        x = np.random.default_rng(0).normal(0, .05, RATE).astype(np.float32); a, b = Enhancer(8, "klar"), Enhancer(8, "klar")
        blk = np.concatenate([a.process(x), a.flush()]); st = np.concatenate([b.process(x[i:i + 1777]) for i in range(0, len(x), 1777)] + [b.flush()])
        np.testing.assert_allclose(blk, st, atol=1e-5); self.assertEqual(len(blk), len(x) + (TAPS - 1) // 2)
    def test_limiter_is_soft_and_bounded(self):
        y = Enhancer(20, "aus").process(np.linspace(-1, 1, 1001, dtype=np.float32))
        self.assertLessEqual(np.abs(y).max(), 1.0); self.assertTrue(np.all(np.diff(y) >= 0))  # nie ueber Vollaussteuerung, monoton
        z = Enhancer(8, "aus").process(np.array([0.5, 0.6], np.float32)); self.assertTrue(np.all(z < 1.0) and z[1] > z[0])
    def test_leveler_evens_out_sentence_levels(self):
        rng = np.random.default_rng(2); db = lambda v: 10 * np.log10(np.mean(v ** 2))
        loud = rng.normal(0, 10 ** (-24 / 20), RATE * 2).astype(np.float32); quiet = rng.normal(0, 10 ** (-32 / 20), RATE * 2).astype(np.float32)
        lv = Leveler(); a = lv.process(loud); lv.process(np.zeros(RATE // 2, np.float32)); b = lv.process(quiet)
        self.assertLess(abs(db(a[RATE:]) - db(b[RATE:])), 3.0)                      # 8 dB Unterschied -> unter 3 dB
        self.assertLess(abs(db(b[RATE:]) - (-29.5)), 2.0)                           # Ziel ca. -29,5 dBFS
    def test_leveler_holds_gain_in_pauses_and_is_bounded(self):
        lv = Leveler(); lv.process(np.random.default_rng(3).normal(0, 0.01, RATE).astype(np.float32)); g = lv.g
        lv.process(np.full(RATE, 1e-5, np.float32)); self.assertAlmostEqual(lv.g, g, places=5)   # Stille zieht nicht hoch
        y = Leveler().process(np.random.default_rng(4).normal(0, 1e-3, RATE).astype(np.float32))
        self.assertLess(np.abs(y).max() / 1e-3, 10 ** (6.1 / 20) * 6)              # hoechstens +6 dB
    def test_enhancer_with_leveler_streams_seamlessly(self):
        x = np.random.default_rng(5).normal(0, .03, RATE).astype(np.float32)
        a = Enhancer(8, "klar", leveler=Leveler()); b = Enhancer(8, "klar", leveler=Leveler())
        blk = np.concatenate([a.process(x), a.flush()]); st = np.concatenate([b.process(x[i:i + 2400]) for i in range(0, len(x), 2400)] + [b.flush()])
        np.testing.assert_allclose(blk, st, atol=1e-5)

if __name__ == "__main__": unittest.main()
