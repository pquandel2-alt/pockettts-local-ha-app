"""Modellpaket importieren (einmalig, offline-faehig) und Installation pruefen.

Das Paket enthaelt zugangsbeschraenkte Modellgewichte (kyutai/pocket-tts, Zustimmung des Nutzers noetig) und
gehoert NICHT ins Image und nicht in ein oeffentliches Repository. Es wird aus dem App-Konfigurationsordner,
aus /share oder (optional, einmalig) aus einer LAN-URL importiert; danach liegt alles dauerhaft in /data.
"""
import hashlib, json, logging, os, re, shutil, tarfile, urllib.request
from dataclasses import dataclass

log = logging.getLogger("importer")
DATA = os.environ.get("DATA_DIR", "/data")
CONFIG = os.environ.get("APP_CONFIG_DIR", "/config")
SHARE = os.environ.get("SHARE_DIR", "/share")
MODELS = f"{DATA}/models_de"; VOICES = f"{DATA}/voices_de"; MARKER = f"{DATA}/.import.json"
REQUIRED = ["flow_lm_flow_int8.onnx", "flow_lm_main_int8.onnx", "mimi_decoder_int8.onnx", "mimi_encoder.onnx",
            "text_conditioner.onnx", "tokenizer.model", "bos_before_voice.npy"]
MEMBER_RE = re.compile(r"^(models_de|voices_de)/[A-Za-z0-9_][A-Za-z0-9_.-]*$")
ALLOWED_EXT = (".onnx", ".npy", ".model", ".wav", ".txt")
PACK_NAMES = ("pockettts-model-pack.tar.gz", "pockettts-model-pack.tar")
MAX_PACK = 2 * 1024**3

class ImportError_(Exception):
    pass

@dataclass
class Install:
    ok: bool
    problems: list

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def check_install() -> Install:
    """Schnelle Pruefung (Vorhandensein + Groesse laut Marker); kein Hashing bei jedem Start."""
    problems = []
    marker = {}
    try:
        with open(MARKER) as f: marker = json.load(f).get("files", {})
    except (OSError, ValueError): pass
    for name in REQUIRED:
        p = f"{MODELS}/{name}"
        if not os.path.isfile(p): problems.append(f"Datei fehlt: models_de/{name}")
        elif marker.get(f"models_de/{name}") is not None and marker[f"models_de/{name}"]["size"] != os.path.getsize(p):
            problems.append(f"Datei beschaedigt (Groesse stimmt nicht): models_de/{name}")
    has_voice = os.path.isdir(VOICES) and any(f.endswith(".wav") for f in os.listdir(VOICES))
    if not has_voice:
        problems.append("Keine Stimmen (*.wav) in voices_de gefunden")
    return Install(not problems, problems)

def _candidates(settings):
    for base in (CONFIG, f"{SHARE}/pockettts"):
        for n in PACK_NAMES:
            p = f"{base}/{n}"
            if os.path.isfile(p): yield ("pack", p)
    if os.path.isdir(f"{CONFIG}/models_de"): yield ("dir", CONFIG)

def _parse_manifest(text):
    m = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64: raise ImportError_(f"Ungueltige Manifest-Zeile: {line[:60]!r}")
        m[parts[1].lstrip("*")] = parts[0].lower()
    return m

def _extract_pack(path, tmp):
    """Sicher entpacken: nur reguläre Dateien, feste Namensmuster, Manifest-Pruefsummen verpflichtend."""
    manifest = None; total = 0
    with tarfile.open(path, "r:*") as t:
        members = t.getmembers()
        for m in members:
            if m.isdir(): continue
            if not m.isreg(): raise ImportError_(f"Unzulaessiger Eintrag im Paket (kein reguläre Datei): {m.name!r}")
            name = m.name.lstrip("./")
            if name == "MANIFEST.sha256":
                manifest = _parse_manifest(t.extractfile(m).read(1 << 20).decode("utf-8")); continue
            if not MEMBER_RE.match(name) or not name.endswith(ALLOWED_EXT): raise ImportError_(f"Unzulaessiger Dateiname im Paket: {m.name!r}")
            total += m.size
            if total > MAX_PACK: raise ImportError_("Paket ist zu gross")
            dst = f"{tmp}/{name}"; os.makedirs(os.path.dirname(dst), exist_ok=True)
            with t.extractfile(m) as src, open(dst, "wb") as out: shutil.copyfileobj(src, out, 1 << 20)
    if manifest is None: raise ImportError_("MANIFEST.sha256 fehlt im Paket - Import abgebrochen (Integritaet nicht pruefbar).")
    return manifest

def _verify(tmp, manifest):
    files = {}
    for sub in ("models_de", "voices_de"):
        d = f"{tmp}/{sub}"
        if not os.path.isdir(d): continue
        for n in sorted(os.listdir(d)):
            rel = f"{sub}/{n}"; want = manifest.get(rel)
            if not want: raise ImportError_(f"Datei nicht im Manifest: {rel}")
            got = sha256_file(f"{d}/{n}")
            if got != want: raise ImportError_(f"Pruefsumme stimmt nicht: {rel}")
            files[rel] = {"sha256": got, "size": os.path.getsize(f"{d}/{n}")}
    missing = [n for n in REQUIRED if f"models_de/{n}" not in files]
    if missing: raise ImportError_("Im Paket fehlen Modelldateien: " + ", ".join(missing))
    if not any(k.startswith("voices_de/") and k.endswith(".wav") for k in files): raise ImportError_("Im Paket sind keine Stimmen (voices_de/*.wav) enthalten.")
    return files

def _install(tmp, files, source):
    os.makedirs(DATA, exist_ok=True)
    for sub in ("models_de", "voices_de"):
        os.makedirs(f"{DATA}/{sub}", exist_ok=True)
        if os.path.isdir(f"{tmp}/{sub}"):
            for n in os.listdir(f"{tmp}/{sub}"):
                os.replace(f"{tmp}/{sub}/{n}", f"{DATA}/{sub}/{n}")   # atomar je Datei; bestehende Caches bleiben (Inhalts-Hash)
    with open(MARKER + ".tmp", "w") as f: json.dump({"source": source, "files": files}, f)
    os.replace(MARKER + ".tmp", MARKER)

def _download(url, dst, expect_sha):
    req = urllib.request.Request(url, headers={"User-Agent": "pockettts-local-int8"})
    h = hashlib.sha256(); n = 0
    with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as out:
        while True:
            b = r.read(1 << 20)
            if not b: break
            n += len(b)
            if n > MAX_PACK: raise ImportError_("Download ist zu gross")
            h.update(b); out.write(b)
    if expect_sha and h.hexdigest() != expect_sha: raise ImportError_("SHA-256 des Downloads stimmt nicht mit import_sha256 ueberein.")
    return h.hexdigest()

def try_import(settings) -> str:
    """Gibt eine Statusmeldung zurueck; wirft ImportError_ mit verstaendlicher Meldung bei defekten Paketen."""
    tmp = f"{DATA}/.import-tmp"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    try:
        for kind, p in _candidates(settings):
            if kind == "pack":
                log.info("Modellpaket gefunden: %s - importiere ...", p); manifest = _extract_pack(p, tmp)
            else:
                log.info("Entpackte Modelle gefunden in %s/models_de - importiere ...", p)
                for sub in ("models_de", "voices_de"):
                    if os.path.isdir(f"{p}/{sub}"): shutil.copytree(f"{p}/{sub}", f"{tmp}/{sub}")
                mf = f"{p}/MANIFEST.sha256"
                if not os.path.isfile(mf): raise ImportError_(f"{mf} fehlt - Integritaet nicht pruefbar.")
                manifest = _parse_manifest(open(mf).read())
            files = _verify(tmp, manifest); _install(tmp, files, os.path.basename(p)); return f"Import aus {os.path.basename(p)} abgeschlossen ({len(files)} Dateien)."
        if settings.import_url:
            host = settings.import_url.split("/")[2]; log.info("Lade Modellpaket einmalig von %s ...", host)
            pack = f"{tmp}/pack.tar.gz"; got = _download(settings.import_url, pack, settings.import_sha256)
            if not settings.import_sha256: log.warning("import_sha256 ist nicht gesetzt - nur das Manifest im Paket wird geprueft (SHA-256 des Downloads: %s).", got)
            manifest = _extract_pack(pack, tmp); os.remove(pack)
            files = _verify(tmp, manifest); _install(tmp, files, "import_url"); return f"Import von {host} abgeschlossen ({len(files)} Dateien)."
        return ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def sync_custom_voices():
    """Eigene Referenz-WAVs aus /config/voices uebernehmen (optional). Der Cache aktualisiert sich ueber den Inhalts-Hash."""
    src = f"{CONFIG}/voices"
    if not os.path.isdir(src): return []
    added = []
    for n in sorted(os.listdir(src)):
        if not n.endswith(".wav") or not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*\.wav$", n): continue
        dst = f"{VOICES}/{n}"
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(f"{src}/{n}") or sha256_file(dst) != sha256_file(f"{src}/{n}"):
            shutil.copyfile(f"{src}/{n}", dst); added.append(n[:-4])
    return added

_bad_logged = set()

def valid_wav(path):
    """Schnellpruefung einer Referenz-WAV (RIFF/WAVE-Header, plausible Groesse)."""
    try:
        if os.path.getsize(path) < 2000: return False
        with open(path, "rb") as f: h = f.read(12)
        return h[:4] == b"RIFF" and h[8:12] == b"WAVE"
    except OSError:
        return False

def voices():
    """Nutzbare Stimmen (gueltige WAVs). Defekte Dateien werden einmal gemeldet und ausgelassen."""
    try: names = sorted(f[:-4] for f in os.listdir(VOICES) if f.endswith(".wav"))
    except OSError: return []
    ok = []
    for n in names:
        if valid_wav(f"{VOICES}/{n}.wav"): ok.append(n)
        elif n not in _bad_logged:
            _bad_logged.add(n); log.warning("Stimme '%s' ist defekt (keine gueltige WAV-Datei) und wird nicht angeboten: %s/%s.wav", n, VOICES, n)
    return ok
