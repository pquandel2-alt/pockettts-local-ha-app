"""Minimaler Supervisor-Mock: nimmt POST /discovery entgegen und schreibt Token-Pruefung + Inhalt in eine Datei."""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n).decode()
        ok = self.headers.get("Authorization") == "Bearer test-token" and self.path == "/discovery"
        with open("/out/discovery.log", "a") as f: f.write(json.dumps({"path": self.path, "auth_ok": ok, "body": json.loads(body)}) + "\n")
        self.send_response(200 if ok else 401); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(b'{"result":"ok","data":{"uuid":"mock"}}')
    def log_message(self, *a): pass
HTTPServer(("0.0.0.0", 80), H).serve_forever()
