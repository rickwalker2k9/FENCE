"""Webhook tools for the Faith voice/chat agent.

    GET  /                       the "Chat with Faith" page and its files (faith/web/)
    POST /tools/fence_estimate   JSON job in, takeoff out (see docs/faith/setup.md)
    GET  /health

Every call must send `x-faith-key` matching FAITH_ASSISTANT_KEY, the same way
Claire's tools send `x-vantage-key`. Standard library only, so it deploys
anywhere (Railway: `python -m faith.server`, PORT is read from the env).
"""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from faith.estimator import EstimateError, estimate

MAX_BODY = 64 * 1024
WEB = Path(__file__).with_name("web")
TYPES = {".html": "text/html; charset=utf-8", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
         ".mp4": "video/mp4", ".webm": "video/webm", ".js": "text/javascript; charset=utf-8"}


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

    def do_GET(self, head_only: bool = False):
        path = self.path.split("?")[0]
        if path == "/health":
            return self._send(200, {"ok": True})
        name = "index.html" if path == "/" else path.lstrip("/")
        file = WEB / name
        if "/" not in name and file.suffix in TYPES and file.is_file():
            return self._file(file, head_only)
        self._send(404, {"error": "not found"})

    def do_HEAD(self):
        self.do_GET(head_only=True)

    def _file(self, file: Path, head_only: bool) -> None:
        # Byte ranges so phones (Safari especially) can stream the video.
        size = file.stat().st_size
        start, end = 0, size - 1
        rng = self.headers.get("range", "")
        if rng.startswith("bytes="):
            a, _, b = rng[6:].split(",")[0].partition("-")
            try:
                start, end = (int(a), int(b) if b else size - 1) if a else (max(size - int(b), 0), size - 1)
            except ValueError:
                start, end = 0, size - 1
            end = min(end, size - 1)
            if start > end:
                self.send_response(416)
                self.send_header("content-range", f"bytes */{size}")
                self.end_headers()
                return
        partial = rng.startswith("bytes=")
        self.send_response(206 if partial else 200)
        self.send_header("content-type", TYPES[file.suffix])
        self.send_header("content-length", str(end - start + 1))
        self.send_header("accept-ranges", "bytes")
        if partial:
            self.send_header("content-range", f"bytes {start}-{end}/{size}")
        self.send_header("cache-control", "no-cache" if file.suffix == ".html" else "public, max-age=3600")
        self.end_headers()
        if head_only:
            return
        with file.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(left, 256 * 1024))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

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
        print("FAITH_ASSISTANT_KEY is not set: the page works, but the takeoff tool refuses every call.")
    port = int(os.environ.get("PORT", "8080"))
    print(f"Faith tools listening on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
