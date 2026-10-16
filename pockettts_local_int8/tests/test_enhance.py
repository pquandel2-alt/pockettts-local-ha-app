import unittest
import numpy as np
from pockettts_app.enhance import Enhancer, curve_fir, PROFILES, RATE, TAPS

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

if __name__ == "__main__": unittest.main()
