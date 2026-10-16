"""Validiert config.yaml und translations/*.yaml mit dem Schema aus dem Supervisor-Quellcode (home-assistant/supervisor)."""
import sys, glob, yaml, os
sys.path.insert(0, "/sup")
from supervisor.apps.validate import SCHEMA_APP_CONFIG, SCHEMA_APP_TRANSLATIONS
from supervisor.apps.options import AppOptions
app = sys.argv[1] if len(sys.argv) > 1 else "/app"
cfg = yaml.safe_load(open(f"{app}/config.yaml"))
out = SCHEMA_APP_CONFIG(cfg)
print("config.yaml: GUELTIG  (slug=%s version=%s arch=%s)" % (out["slug"], out["version"], out["arch"]))
for k in ("init", "boot", "startup", "stage", "discovery", "watchdog", "ports", "map", "backup_exclude", "tmpfs", "homeassistant"):
    print("  %-15s %s" % (k, out.get(k)))
for t in sorted(glob.glob(f"{app}/translations/*.yaml")):
    SCHEMA_APP_TRANSLATIONS(yaml.safe_load(open(t))); print("translation %s: GUELTIG" % os.path.basename(t))
# Optionen gegen das App-Schema (so wie der Supervisor die Nutzereingaben prueft)
ao = AppOptions(None, out["schema"], out["name"], out["slug"], resolve_secrets=False)
print("Standardoptionen: gueltig ->", bool(ao.validate(out["options"])))
for bad in ({"threads": 99}, {"default_voice": "nobody"}, {"log_level": "loud"}, {"import_sha256": "xyz"}, {"streaming": "ja"}, {"first_chunk": 0}, {"main_model": "fp16"}):
    try: ao.validate({**out["options"], **bad}); print("  FEHLER: wurde NICHT abgelehnt:", bad)
    except Exception as e: print("  abgelehnt wie erwartet:", bad)
good = {**out["options"], "import_url": "http://nas.local:8000/pockettts-model-pack.tar.gz", "import_sha256": "a"*64, "threads": 4}
print("Optionen mit Import-URL: gueltig ->", bool(ao.validate(good)))
for f in ("icon.png", "logo.png", "README.md", "DOCS.md", "CHANGELOG.md"):
    print("  %-12s %s" % (f, "vorhanden" if os.path.exists(f"{app}/{f}") else "FEHLT"))
