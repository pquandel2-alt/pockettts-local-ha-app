import json, os, tempfile, unittest
from pockettts_app import settings as cfg

class Settings(unittest.TestCase):
    def test_defaults_match_measured_optimum(self):
        s = cfg.parse({})
        self.assertEqual((s.threads, s.main_model, s.first_chunk, s.max_chunk, s.prebuffer_ms, s.lead_in_ms, s.default_voice), (3, "fp32", 2, 4, 150, 0, "juergen"))
        self.assertTrue(s.streaming and s.warmup and s.normalize_text); self.assertFalse(s.ort_spinning)
        self.assertEqual((s.volume_boost_db, s.sound_profile), (8, "klar"))
    def test_invalid_values(self):
        for bad in ({"threads": 0}, {"threads": 99}, {"threads": "2"}, {"threads": True}, {"first_chunk": 0}, {"prebuffer_ms": -1}, {"streaming": "yes"},
                    {"language": "en"}, {"log_level": "trace"}, {"default_voice": "../x"}, {"default_voice": ""}, {"first_chunk": 5, "max_chunk": 4},
                    {"temperature": 0.0}, {"temperature": 1.5}, {"temperature": "warm"}, {"import_url": "ftp://x/y"}, {"import_sha256": "abc"},
                    {"main_model": "fp16"}, {"main_model": ""},
                    {"volume_boost_db": -1}, {"volume_boost_db": 21}, {"sound_profile": "hell"}, {"sound_profile": 1}):
            with self.subTest(bad), self.assertRaises(cfg.SettingsError): cfg.parse(bad)
    def test_old_treble_option_from_103_is_ignored(self):
        self.assertEqual(cfg.parse({"treble_boost_db": 8, "sound_profile": "weich"}).sound_profile, "weich")
    def test_main_model_int8(self):
        self.assertEqual(cfg.parse({"main_model": "int8"}).main_model, "int8")
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
