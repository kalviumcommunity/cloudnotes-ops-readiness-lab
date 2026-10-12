"""Local CloudNotes application; Python standard library only."""
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SERVICE = "cloudnotes-api"
NOTES = [
    {"id": "n1", "text": "Team meeting notes"},
    {"id": "n2", "text": "Release checklist"},
    {"id": "n3", "text": "Support handover"},
]
METRICS = """cloudnotes_requests_total 1000
cloudnotes_errors_total 20
cloudnotes_request_latency_seconds 0.084
cloudnotes_saturation_ratio 0.41
"""


def write_backup(directory):
    """Write acknowledged notes only within the supplied directory."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "notes.json"
    if destination.is_symlink():
        raise ValueError("Backup file must not be a symlink")
    destination.write_text(json.dumps(NOTES, indent=2) + "\n", encoding="utf-8")
    return destination


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"status": "ok", "service": SERVICE})
        elif self.path == "/metrics":
            self.respond(200, METRICS, "text/plain; version=0.0.4; charset=utf-8")
        elif self.path == "/logs":
            timestamp = datetime.now(timezone.utc).isoformat()
            self.respond(200, [
                {"timestamp": timestamp, "level": "INFO", "service": SERVICE,
                 "msg": "Request completed"},
                {"timestamp": timestamp, "level": "ERROR", "service": SERVICE,
                 "msg": "Request failed"},
            ])
        else:
            self.respond(404, {"error": "not found"})

    def respond(self, status, body, content_type="application/json"):
        payload = (json.dumps(body) if content_type == "application/json" else body)
        payload = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def create_server():
    return ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
