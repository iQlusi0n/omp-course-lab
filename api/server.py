"""HTTP front-end for the lab: JSON API + static files from web/.

Run with ``python -m api`` (port 8080). Everything is stdlib ``http.server``.
"""

from __future__ import annotations

import json
import mimetypes
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import db

SERVICE_NAME = "omp-course-lab orders api (conflict-lab branch)"
VERSION = "1.0"
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

_USER_ROUTE = re.compile(r"^/users/(\d+)$")


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


class LabHandler(BaseHTTPRequestHandler):
    server_version = "LabAPI/" + VERSION

    # ----- plumbing -------------------------------------------------------

    def log_message(self, fmt, *args):  # quieter than the default
        if getattr(self.server, "quiet", False):
            return
        super().log_message(fmt, *args)

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            raise BadRequest("empty request body")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise BadRequest(f"invalid JSON: {e}") from None
        if not isinstance(data, dict):
            raise BadRequest("JSON body must be an object")
        return data

    def _dispatch(self, handler) -> None:
        try:
            handler()
        except NotFound as e:
            self._send_json(404, {"error": str(e) or "not found"})
        except BadRequest as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:  # keep the server alive, expose the cause
            self._send_json(
                500,
                {"error": "internal error", "detail": repr(e),
                 "trace": traceback.format_exc().splitlines()[-3:]},
            )

    # ----- routing --------------------------------------------------------

    def do_GET(self) -> None:
        self._dispatch(self._get)

    def do_POST(self) -> None:
        self._dispatch(self._post)

    def do_DELETE(self) -> None:
        self._dispatch(self._delete)

    def _get(self) -> None:
        url = urlsplit(self.path)
        params = parse_qs(url.query)
        path = url.path

        if path == "/health":
            self._send_json(200, {"status": "ok", "service": SERVICE_NAME, "version": VERSION})
            return

        m = _USER_ROUTE.match(path)
        if m:
            self._get_user(int(m.group(1)))
            return

        if path == "/orders":
            self._list_orders(params)
            return

        self._static(path)

    def _post(self) -> None:
        path = urlsplit(self.path).path
        if path == "/signup":
            self._signup()
            return
        raise NotFound(f"no POST route for {path}")

    def _delete(self) -> None:
        path = urlsplit(self.path).path
        raise NotFound(f"no DELETE route for {path}")

    # ----- handlers -------------------------------------------------------

    def _get_user(self, user_id: int) -> None:
        user = db.get_user(user_id)
        if user is None:
            raise NotFound(f"user {user_id} not found")
        # NOTE: order_count is computed inside get_user before any paging is
        # applied; if counts ever look stale, check the seed (tools/seed_db.py).
        self._send_json(200, user)

    def _list_orders(self, params: dict) -> None:
        month = params.get("month", [None])[0]
        if month is not None and not re.fullmatch(r"\d{4}-\d{2}", month):
            raise BadRequest("month must be YYYY-MM")
        try:
            page = int(params.get("page", ["1"])[0])
        except ValueError:
            raise BadRequest("page must be an integer") from None
        if page < 1:
            raise BadRequest("page must be >= 1")

        offset = page * db.PAGE_SIZE
        orders = db.list_orders(month=month, limit=db.PAGE_SIZE, offset=offset)
        self._send_json(
            200,
            {
                "month": month,
                "page": page,
                "page_size": db.PAGE_SIZE,
                "count": db.count_orders_in_month(month),
                "orders": orders,
            },
        )

    def _signup(self) -> None:
        data = self._read_json()
        user = db.create_user(data["name"], data["email"])
        self._send_json(201, user)

    def _static(self, path: str) -> None:
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT not in target.parents or not target.is_file():
            raise NotFound(f"no route for {path}")
        body = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(host: str = "127.0.0.1", port: int = 8080, quiet: bool = False) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), LabHandler)
    server.daemon_threads = True
    server.quiet = quiet
    return server
