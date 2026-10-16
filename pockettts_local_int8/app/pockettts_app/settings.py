"""App-Optionen laden und validieren (Supervisor validiert das Schema bereits, wir pruefen erneut und feldübergreifend)."""
import json, os
from dataclasses import dataclass

VOICES_BUILTIN = ["juergen", "bill_boerst", "charles", "daan", "george", "giovanni", "michael", "paul", "peter_yearsley", "rafael", "stuart_bell"]
LOG_LEVELS = ("debug", "info", "warning", "error")
MAIN_MODELS = ("fp32", "int8")
SOUND_PROFILES = ("klar", "weich", "aus")

class SettingsError(ValueError):
    pass

@dataclass(frozen=True)
class Settings:
    language: str = "de"
    default_voice: str = "juergen"
    threads: int = 3
    main_model: str = "fp32"
    streaming: bool = True
    first_chunk: int = 2
    max_chunk: int = 4
    prebuffer_ms: int = 150
    lead_in_ms: int = 0
    warmup: bool = True
    preload_voices: bool = True
    normalize_text: bool = True
    ort_spinning: bool = False
    temperature: float = 0.7
    volume_boost_db: int = 8
    sound_profile: str = "klar"
    log_level: str = "info"
    import_url: str = ""
    import_sha256: str = ""

def _int(o, key, lo, hi, default):
    v = o.get(key, default)
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise SettingsError(f"Option '{key}' muss eine ganze Zahl zwischen {lo} und {hi} sein (ist: {v!r}).")
    return v

def _bool(o, key, default):
    v = o.get(key, default)
    if not isinstance(v, bool):
        raise SettingsError(f"Option '{key}' muss true oder false sein (ist: {v!r}).")
    return v

def _float(o, key, lo, hi, default):
    v = o.get(key, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= float(v) <= hi:
        raise SettingsError(f"Option '{key}' muss eine Zahl zwischen {lo} und {hi} sein (ist: {v!r}).")
    return float(v)

def parse(o: dict) -> Settings:
    d = Settings()
    language = o.get("language", d.language)
    if language != "de":
        raise SettingsError(f"Nicht unterstuetzte Sprache '{language}'. Dieses Modellpaket kann nur 'de'.")
    voice = o.get("default_voice", d.default_voice)
    if not isinstance(voice, str) or not voice or "/" in voice or voice.startswith("."):
        raise SettingsError(f"Ungueltige Standardstimme: {voice!r}")
    level = o.get("log_level", d.log_level)
    if level not in LOG_LEVELS:
        raise SettingsError(f"log_level muss eines von {LOG_LEVELS} sein (ist: {level!r}).")
    main_model = o.get("main_model", d.main_model)
    if main_model not in MAIN_MODELS:
        raise SettingsError(f"main_model muss eines von {MAIN_MODELS} sein (ist: {main_model!r}).")
    sound_profile = o.get("sound_profile", d.sound_profile)
    if sound_profile not in SOUND_PROFILES:
        raise SettingsError(f"sound_profile muss eines von {SOUND_PROFILES} sein (ist: {sound_profile!r}).")
    s = Settings(
        language=language, default_voice=voice,
        threads=_int(o, "threads", 1, 8, d.threads), main_model=main_model,
        streaming=_bool(o, "streaming", d.streaming),
        first_chunk=_int(o, "first_chunk", 1, 15, d.first_chunk),
        max_chunk=_int(o, "max_chunk", 1, 30, d.max_chunk),
        prebuffer_ms=_int(o, "prebuffer_ms", 0, 3000, d.prebuffer_ms),
        lead_in_ms=_int(o, "lead_in_ms", 0, 1000, d.lead_in_ms),
        warmup=_bool(o, "warmup", d.warmup), preload_voices=_bool(o, "preload_voices", d.preload_voices),
        normalize_text=_bool(o, "normalize_text", d.normalize_text), ort_spinning=_bool(o, "ort_spinning", d.ort_spinning),
        temperature=_float(o, "temperature", 0.1, 1.0, d.temperature),
        volume_boost_db=_int(o, "volume_boost_db", 0, 20, d.volume_boost_db), sound_profile=sound_profile,
        log_level=level, import_url=str(o.get("import_url") or ""), import_sha256=str(o.get("import_sha256") or "").lower(),
    )
    if s.max_chunk < s.first_chunk:
        raise SettingsError(f"max_chunk ({s.max_chunk}) darf nicht kleiner als first_chunk ({s.first_chunk}) sein.")
    if s.import_url and not s.import_url.lower().startswith(("http://", "https://")):
        raise SettingsError("import_url muss mit http:// oder https:// beginnen.")
    if s.import_sha256 and (len(s.import_sha256) != 64 or any(c not in "0123456789abcdef" for c in s.import_sha256)):
        raise SettingsError("import_sha256 muss ein 64-stelliger Hex-Wert sein.")
    return s

def load(path: str = None) -> Settings:
    path = path or os.environ.get("OPTIONS_PATH", "/data/options.json")
    try:
        with open(path, encoding="utf-8") as f: raw = json.load(f)
    except FileNotFoundError:
        raw = {}                                   # lokaler Test ohne Supervisor: Standardwerte
    except json.JSONDecodeError as e:
        raise SettingsError(f"{path} ist kein gueltiges JSON: {e}")
    return parse(raw)
