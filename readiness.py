"""Sequential readiness checks for the local CloudNotes application."""
import argparse
import json
from pathlib import Path
import sys
from threading import Thread
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

from app.app import NOTES, create_server, write_backup

ROOT = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8765"
SIGNALS = (
    "cloudnotes_requests_total",
    "cloudnotes_errors_total",
    "cloudnotes_request_latency_seconds",
    "cloudnotes_saturation_ratio",
)
OPENER = build_opener(ProxyHandler({}))


def config(name):
    """Read the flat key/value YAML subset used by this lab (no dependencies)."""
    values = {}
    for line in (ROOT / "ops" / f"{name}.yaml").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise ValueError(f"Invalid configuration line: {line}")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def fetch(path):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Endpoint must be a local absolute path")
    try:
        with OPENER.open(BASE_URL + path, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")


def signals():
    path = config("signals")["metrics_path"]
    status, body = fetch(path)
    print(f"TASK1 metrics_path={path} HTTP {status}")
    samples = {}
    if status == 200:
        for line in body.splitlines():
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) == 2:
                    samples[parts[0]] = float(parts[1])
    if status != 200 or not all(name in samples for name in SIGNALS):
        print("TASK1 FAIL")
        return False
    for name in SIGNALS:
        print(f"{name} {samples[name]:g}")
    requests = samples["cloudnotes_requests_total"]
    errors = samples["cloudnotes_errors_total"]
    objective = 99.0
    allowed = requests * (100.0 - objective) / 100.0
    print(f"requests={requests:g}")
    print(f"errors={errors:g}")
    print(f"objective_percent={objective:.1f}")
    print(f"allowed_errors={allowed:g}")
    print(f"error_budget_remaining={allowed - errors:g}")
    print("TASK1 PASS")
    return True


def logs():
    if not signals():
        print("TASK2 SKIP signals not ready")
        return False
    field = config("logging")["level_field"]
    print(f"TASK2 level_field={field}")
    status, body = fetch("/logs")
    records = json.loads(body) if status == 200 else []
    matches = [record for record in records
               if record.get("service") == "cloudnotes-api" and record.get(field) == "ERROR"]
    if not matches:
        print("TASK2 FAIL")
        return False
    print(json.dumps(matches[0], sort_keys=True))
    print("TASK2 PASS")
    return True


def recovery():
    if not logs():
        print("TASK3 SKIP logs not ready")
        return False
    settings = config("recovery")
    directory = settings["backup_dir"]
    print(f"TASK3 backup_dir={directory}")
    target = (ROOT / directory).resolve()
    if target != (ROOT / "data" / "notes-backup").resolve():
        print("TASK3 FAIL")
        return False
    backup = write_backup(target)
    restored = json.loads(backup.read_text(encoding="utf-8"))
    ids = [note["id"] for note in restored]
    if restored != NOTES or ids != ["n1", "n2", "n3"]:
        print("TASK3 FAIL")
        return False
    print(f"rpo_minutes={int(settings['rpo_minutes'])}")
    print(f"rto_seconds={int(settings['rto_seconds'])}")
    print(f"restored_ids={','.join(ids)}")
    print("TASK3 PASS")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("signals", "logs", "recovery"))
    args = parser.parse_args()
    try:
        server = create_server()
    except OSError as error:
        print(f"TOOL ERROR: cannot start {BASE_URL}: {error}. Contact instructor.", file=sys.stderr)
        return 2
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return 0 if {"signals": signals, "logs": logs, "recovery": recovery}[args.task]() else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"TOOL ERROR: {error}. Contact instructor.", file=sys.stderr)
        return 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    sys.exit(main())
