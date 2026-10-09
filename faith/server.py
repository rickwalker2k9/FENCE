"""Webhook tools for the Faith voice/chat agent.

    POST /tools/fence_estimate   JSON job in, takeoff out (see docs/faith/tools.md)
    GET  /health

Every call must send `x-faith-key` matching FAITH_ASSISTANT_KEY, the same way
Claire's tools send `x-vantage-key`. Standard library only, so it deploys
anywhere (Railway: `python -m faith.server`, PORT is read from the env).
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from faith.estimator import EstimateError, estimate

MAX_BODY = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "Faith/1"

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self) -> bool:
        key = os.environ.get("FAITH_ASSISTANT_KEY", "")
        sent = self.headers.get("x-faith-key", "")
        return bool(key) and hmac.compare_digest(key.encode(), sent.encode())

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/tools/fence_estimate":
            return self._send(404, {"error": "not found"})
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        length = int(self.headers.get("content-length") or 0)
        if length > MAX_BODY:
            return self._send(413, {"error": "request too large"})
        try:
            job = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(job, dict):
                raise ValueError
        except ValueError:
            return self._send(400, {"error": "body must be a JSON object"})
        try:
            self._send(200, estimate(job))
        except EstimateError as e:
            # 200 so the agent reads the question back instead of an error.
            self._send(200, {"needs": str(e), "spoken": str(e)})

    def log_message(self, fmt, *args):  # keep job details out of logs
        pass


def main() -> None:
    if not os.environ.get("FAITH_ASSISTANT_KEY"):
        raise SystemExit("Set FAITH_ASSISTANT_KEY before starting the tool server.")
    port = int(os.environ.get("PORT", "8080"))
    print(f"Faith tools listening on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
