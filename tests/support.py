"""Shared helpers: temp copy of the seeded DB, in-process API server, CLI runner."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_DB = ROOT / "data" / "lab.sqlite"
sys.path.insert(0, str(ROOT))

from api.server import make_server  # noqa: E402


class TempDB:
    """Copy data/lab.sqlite to a temp file and point DATABASE_URL at it."""

    def __enter__(self) -> "TempDB":
        self.dir = tempfile.mkdtemp(prefix="lab-")
        self.path = os.path.join(self.dir, "lab.sqlite")
        shutil.copy(SEED_DB, self.path)
        self.old = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = self.path
        return self

    def __exit__(self, *exc) -> None:
        if self.old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.old
        shutil.rmtree(self.dir, ignore_errors=True)


class LiveServer:
    """Run the API on an ephemeral port in a background thread."""

    def __enter__(self) -> "LiveServer":
        self.server = make_server("127.0.0.1", 0, quiet=True)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict | bytes]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status, raw, ctype = resp.status, resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            status, raw, ctype = e.code, e.read(), e.headers.get("Content-Type", "")
        if ctype.startswith("application/json"):
            return status, json.loads(raw)
        return status, raw

    def get(self, path: str):
        return self.request("GET", path)

    def post(self, path: str, body: dict):
        return self.request("POST", path, body)


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run ``python -m cli ...`` from the repo root with the current env."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "cli", *args],
        cwd=ROOT, env=full_env, capture_output=True, text=True, timeout=20,
    )
