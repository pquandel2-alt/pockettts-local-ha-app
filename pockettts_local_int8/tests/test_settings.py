import json, os, tempfile, unittest
from pockettts_app import settings as cfg

class Settings(unittest.TestCase):
    def test_defaults_match_measured_optimum(self):
        s = cfg.parse({})
        self.assertEqual((s.threads, s.first_chunk, s.max_chunk, s.prebuffer_ms, s.lead_in_ms, s.default_voice), (2, 2, 4, 150, 0, "juergen"))
        self.assertTrue(s.streaming and s.warmup and s.normalize_text); self.assertFalse(s.ort_spinning)
    def test_invalid_values(self):
        for bad in ({"threads": 0}, {"threads": 99}, {"threads": "2"}, {"threads": True}, {"first_chunk": 0}, {"prebuffer_ms": -1}, {"streaming": "yes"},
                    {"language": "en"}, {"log_level": "trace"}, {"default_voice": "../x"}, {"default_voice": ""}, {"first_chunk": 5, "max_chunk": 4},
                    {"temperature": 0.0}, {"temperature": 1.5}, {"temperature": "warm"}, {"import_url": "ftp://x/y"}, {"import_sha256": "abc"}):
            with self.subTest(bad), self.assertRaises(cfg.SettingsError): cfg.parse(bad)
    def test_load_missing_file_uses_defaults(self):
        self.assertEqual(cfg.load("/nonexistent/options.json"), cfg.Settings())
    def test_load_broken_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f: f.write("{nope")
        with self.assertRaises(cfg.SettingsError): cfg.load(f.name)
        os.unlink(f.name)
    def test_load_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f: json.dump({"threads": 3, "default_voice": "paul"}, f)
        s = cfg.load(f.name); self.assertEqual((s.threads, s.default_voice), (3, "paul")); os.unlink(f.name)

if __name__ == "__main__": unittest.main()
