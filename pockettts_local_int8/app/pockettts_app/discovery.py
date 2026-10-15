"""Meldet den Wyoming-Dienst beim Supervisor (POST /discovery); Home Assistant bietet dann die Einrichtung an."""
import json, logging, os, socket, urllib.request

log = logging.getLogger("discovery")

def send(port):
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        log.info("Kein SUPERVISOR_TOKEN - Discovery uebersprungen (lokaler Test).")
        return False
    body = json.dumps({"service": "wyoming", "config": {"uri": f"tcp://{socket.gethostname()}:{port}"}}).encode()
    req = urllib.request.Request("http://supervisor/discovery", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r: ok = 200 <= r.status < 300
    except Exception as e:
        log.error("Discovery-Nachricht an Home Assistant fehlgeschlagen: %r", e); return False
    log.info("Discovery-Information an Home Assistant gesendet." if ok else "Discovery wurde abgelehnt.")
    return ok
