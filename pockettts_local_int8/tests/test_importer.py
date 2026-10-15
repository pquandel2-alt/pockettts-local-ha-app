import hashlib, importlib, io, os, tarfile, tempfile, unittest

class Importer(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        for k, sub in (("DATA_DIR", "data"), ("APP_CONFIG_DIR", "config"), ("SHARE_DIR", "share")):
            os.makedirs(f"{self.d}/{sub}"); os.environ[k] = f"{self.d}/{sub}"
        from pockettts_app import importer; self.imp = importlib.reload(importer)
        from pockettts_app import settings as cfg; self.s = cfg.Settings()

    def _pack(self, path, extra=None, manifest=True, corrupt=None, omit=None):
        files = {f"models_de/{n}": f"data-{n}".encode() for n in self.imp.REQUIRED if n != omit}
        files["voices_de/juergen.wav"] = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 3000
        files.update(extra or {})
        lines = "".join(f"{hashlib.sha256(v).hexdigest()}  {k}\n" for k, v in files.items())
        with tarfile.open(path, "w:gz") as t:
            for k, v in files.items():
                if corrupt == k: v = v + b"x"
                ti = tarfile.TarInfo(k); ti.size = len(v); t.addfile(ti, io.BytesIO(v))
            if manifest:
                m = lines.encode(); ti = tarfile.TarInfo("MANIFEST.sha256"); ti.size = len(m); t.addfile(ti, io.BytesIO(m))
        return path

    def test_missing_install_is_reported(self):
        r = self.imp.check_install(); self.assertFalse(r.ok); self.assertTrue(any("models_de" in p for p in r.problems))

    def test_import_ok_from_config_pack(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz")
        msg = self.imp.try_import(self.s); self.assertIn("abgeschlossen", msg)
        self.assertTrue(self.imp.check_install().ok); self.assertEqual(self.imp.voices(), ["juergen"])
        self.assertFalse(os.path.exists(f"{os.environ['DATA_DIR']}/.import-tmp"))

    def test_import_from_share(self):
        os.makedirs(f"{os.environ['SHARE_DIR']}/pockettts"); self._pack(f"{os.environ['SHARE_DIR']}/pockettts/pockettts-model-pack.tar.gz")
        self.assertIn("abgeschlossen", self.imp.try_import(self.s))

    def test_checksum_mismatch_rejected(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz", corrupt="models_de/tokenizer.model")
        with self.assertRaisesRegex(self.imp.ImportError_, "Pruefsumme"): self.imp.try_import(self.s)
        self.assertFalse(self.imp.check_install().ok)

    def test_missing_manifest_rejected(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz", manifest=False)
        with self.assertRaisesRegex(self.imp.ImportError_, "MANIFEST"): self.imp.try_import(self.s)

    def test_missing_model_file_rejected(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz", omit="bos_before_voice.npy")
        with self.assertRaisesRegex(self.imp.ImportError_, "bos_before_voice"): self.imp.try_import(self.s)

    def test_path_traversal_rejected(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz", extra={"models_de/../../evil.onnx": b"x"})
        with self.assertRaises(self.imp.ImportError_): self.imp.try_import(self.s)
        self.assertFalse(os.path.exists(f"{self.d}/evil.onnx"))

    def test_symlink_rejected(self):
        p = f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz"
        with tarfile.open(p, "w:gz") as t:
            ti = tarfile.TarInfo("models_de/x.onnx"); ti.type = tarfile.SYMTYPE; ti.linkname = "/etc/passwd"; t.addfile(ti)
        with self.assertRaises(self.imp.ImportError_): self.imp.try_import(self.s)

    def test_damaged_file_detected_after_install(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz"); self.imp.try_import(self.s)
        with open(f"{self.imp.MODELS}/tokenizer.model", "ab") as f: f.write(b"damage")
        r = self.imp.check_install(); self.assertFalse(r.ok); self.assertTrue(any("tokenizer.model" in p for p in r.problems))

    def test_custom_voices_sync_and_update(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz"); self.imp.try_import(self.s)
        os.makedirs(f"{os.environ['APP_CONFIG_DIR']}/voices"); p = f"{os.environ['APP_CONFIG_DIR']}/voices/meine_stimme.wav"
        open(p, "wb").write(b"RIFF\x00\x00\x00\x00WAVE" + b"A" * 3000); self.assertEqual(self.imp.sync_custom_voices(), ["meine_stimme"]); self.assertIn("meine_stimme", self.imp.voices())
        self.assertEqual(self.imp.sync_custom_voices(), [])           # unveraendert -> nichts zu tun
        open(p, "wb").write(b"RIFF\x00\x00\x00\x00WAVE" + b"B" * 3000); self.assertEqual(self.imp.sync_custom_voices(), ["meine_stimme"])   # geaendert -> aktualisiert

    def test_corrupt_voice_is_not_offered(self):
        self._pack(f"{os.environ['APP_CONFIG_DIR']}/pockettts-model-pack.tar.gz"); self.imp.try_import(self.s)
        open(f"{self.imp.VOICES}/kaputt.wav", "wb").write(b"\x00" * 500); open(f"{self.imp.VOICES}/zufall.wav", "wb").write(os.urandom(5000))
        self.assertEqual(self.imp.voices(), ["juergen"])

if __name__ == "__main__": unittest.main()
