#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat server for the provider/fallback exercises.

    python3 tools/mock-provider.py                # http://127.0.0.1:8765
    python3 tools/mock-provider.py --port 9000
    python3 tools/mock-provider.py --fail         # every completion -> HTTP 429

Endpoints (with or without the /v1 prefix):
    GET  /v1/models            -> {"object":"list","data":[{"id":"mock-1",...}]}
    POST /v1/chat/completions  -> canned reply; honours "stream": true (SSE)

No authentication. Every request line is logged to stderr. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockHandler(BaseHTTPRequestHandler):
    server_version = "mock-provider/1.0"
    model_id = "mock-1"
    fail = False

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[mock-provider] {self.command} {self.path} -> {fmt % args}\n")

    # ----- helpers --------------------------------------------------------

    def _json(self, status: int, payload, extra_headers: dict | None = None) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _route(self) -> str:
        path = self.path.split("?", 1)[0].rstrip("/")
        return path[3:] if path.startswith("/v1") else path

    def _reply_text(self, req: dict) -> str:
        last_user = ""
        for msg in req.get("messages", []):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):  # multi-part content
                    content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
                last_user = str(content)
        snippet = last_user.strip().replace("\n", " ")[:80]
        return f"Hello from {self.model_id}. You said: {snippet}"

    # ----- routes ---------------------------------------------------------

    def do_GET(self) -> None:
        route = self._route()
        if route == "/models":
            self._json(200, {
                "object": "list",
                "data": [{"id": self.model_id, "object": "model", "created": 1700000000, "owned_by": "lab"}],
            })
        elif route in ("", "/health"):
            self._json(200, {"status": "ok", "model": self.model_id, "fail": self.fail})
        else:
            self._json(404, {"error": {"message": f"unknown route {self.path}", "type": "invalid_request_error"}})

    def do_POST(self) -> None:
        route = self._route()
        if route != "/chat/completions":
            self._json(404, {"error": {"message": f"unknown route {self.path}", "type": "invalid_request_error"}})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": {"message": "invalid JSON body", "type": "invalid_request_error"}})
            return

        if self.fail:
            self._json(429, {
                "error": {"message": "rate limited (mock --fail)", "type": "rate_limit_error", "code": "rate_limited"},
            }, {"Retry-After": "1"})
            return

        text = self._reply_text(req)
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())
        if req.get("stream"):
            self._stream(completion_id, created, text)
        else:
            self._json(200, {
                "id": completion_id,
                "object": "chat.completion",
                "created": created,
                "model": self.model_id,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 8, "completion_tokens": len(text.split()), "total_tokens": 8 + len(text.split())},
            })

    def _stream(self, completion_id: str, created: int, text: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def chunk(delta: dict, finish=None) -> None:
            payload = {
                "id": completion_id, "object": "chat.completion.chunk", "created": created,
                "model": self.model_id,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }
            self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
            self.wfile.flush()

        chunk({"role": "assistant", "content": ""})
        for word in text.split(" "):
            chunk({"content": word + " "})
            time.sleep(0.02)
        chunk({}, finish="stop")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default="mock-1", help="model id to advertise")
    parser.add_argument("--fail", action="store_true", help="answer every completion with HTTP 429")
    args = parser.parse_args(argv)

    MockHandler.model_id = args.model
    MockHandler.fail = args.fail
    server = ThreadingHTTPServer((args.host, args.port), MockHandler)
    server.daemon_threads = True
    mode = "FAIL mode (429 on completions)" if args.fail else "normal mode"
    print(f"mock-provider serving model '{args.model}' on http://{args.host}:{args.port}/v1 in {mode}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
