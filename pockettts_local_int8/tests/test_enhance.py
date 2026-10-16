import unittest
import numpy as np
from pockettts_app.enhance import Enhancer, shelf_fir, RATE, TAPS

class Enhance(unittest.TestCase):
    def test_off_is_identity(self):
        x = np.random.default_rng(1).normal(0, .1, 5000).astype(np.float32); e = Enhancer(0, 0)
        np.testing.assert_array_equal(e.process(x), x); self.assertEqual(e.flush().size, 0)
    def test_shelf_response(self):
        f = np.fft.rfftfreq(8192, 1 / RATE); H = 20 * np.log10(np.abs(np.fft.rfft(shelf_fir(8), 8192)))
        at = lambda fr: H[np.argmin(abs(f - fr))]
        self.assertAlmostEqual(at(300), 0, delta=0.2); self.assertAlmostEqual(at(1000), 0, delta=0.2); self.assertAlmostEqual(at(6000), 8, delta=0.3)
    def test_streaming_equals_block(self):
        x = np.random.default_rng(0).normal(0, .05, RATE).astype(np.float32); a, b = Enhancer(8, 8), Enhancer(8, 8)
        blk = np.concatenate([a.process(x), a.flush()]); st = np.concatenate([b.process(x[i:i + 1777]) for i in range(0, len(x), 1777)] + [b.flush()])
        np.testing.assert_allclose(blk, st, atol=1e-6); self.assertEqual(len(blk), len(x) + (TAPS - 1) // 2)
    def test_limiter_is_soft_and_bounded(self):
        y = Enhancer(20, 0).process(np.linspace(-1, 1, 1001, dtype=np.float32))
        self.assertLessEqual(np.abs(y).max(), 1.0); self.assertTrue(np.all(np.diff(y) >= 0))  # nie ueber Vollaussteuerung, monoton
        z = Enhancer(8, 0).process(np.array([0.5, 0.6], np.float32)); self.assertTrue(np.all(z < 1.0) and z[1] > z[0])   # typische Spitzen: weich, nicht abgeschnitten

if __name__ == "__main__": unittest.main()
